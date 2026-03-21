from __future__ import annotations

import asyncio
import json
import os
from base64 import b64encode
from typing import Any, Dict
from unittest.mock import AsyncMock, patch

import pytest
from starlette.testclient import TestClient
from itsdangerous import TimestampSigner

from src.app.main import app
from src.db.sqlite import connect, create_all_tables_async


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def db_with_user(tmp_path, monkeypatch: pytest.MonkeyPatch) -> str:
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("SQLITE_DB_PATH", str(db_path))

    async def setup() -> None:
        conn = await connect(db_path)
        await create_all_tables_async(conn)
        await conn.execute(
            """
            INSERT INTO users (id, github_username, access_token, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("u1", "testlogin", "test_access_token", "2026-03-01", "2026-03-01"),
        )
        await conn.commit()
        await conn.close()

    _run(setup())
    return str(db_path)


def _set_session(client: TestClient, data: Dict[str, Any]) -> None:
    secret_key = os.getenv("SESSION_SECRET", "dev-secret")
    payload = b64encode(json.dumps(data).encode("utf-8"))
    signed = TimestampSigner(secret_key).sign(payload).decode("utf-8")
    client.cookies.set("session", signed, path="/")


def test_github_repos_requires_session(client: TestClient) -> None:
    response = client.get("/api/github/repos")
    assert response.status_code == 401
    assert response.json()["error"] == "UNAUTHORIZED"


def test_github_repos_success(
    client: TestClient,
    db_with_user: str,
) -> None:
    _set_session(client, {"user_id": "u1"})

    fake_repos = {
        "repos": [
            {
                "id": 123,
                "full_name": "owner/repo-a",
                "description": "desc",
                "private": False,
                "language": "Python",
                "stargazers_count": 10,
                "forks_count": 2,
                "default_branch": "main",
                "pushed_at": "2026-01-01T00:00:00Z",
            }
        ],
        "page": 1,
        "per_page": 30,
        "total_count": 1,
    }

    with patch(
        "src.api.github.github_repos.list_user_repos",
        new=AsyncMock(return_value=fake_repos),
    ) as _:
        response = client.get("/api/github/repos?page=1&per_page=30")

    assert response.status_code == 200
    body = response.json()
    assert body["repos"][0]["full_name"] == "owner/repo-a"


def test_selected_repos_put_requires_fields(
    client: TestClient,
    db_with_user: str,
) -> None:
    _set_session(client, {"user_id": "u1"})

    response = client.put("/api/user/selected-repos", json={})
    assert response.status_code == 400
    assert response.json()["error"] == "BAD_REQUEST"


def test_selected_repos_put_and_get(
    client: TestClient,
    db_with_user: str,
) -> None:
    _set_session(client, {"user_id": "u1"})

    response = client.put(
        "/api/user/selected-repos",
        json={"full_names": ["owner/repo-a", "owner/repo-b"], "replace": True},
    )
    assert response.status_code == 200
    assert len(response.json()["selected_repos"]) == 2

    response2 = client.get("/api/user/selected-repos")
    assert response2.status_code == 200
    items = response2.json()["selected_repos"]
    assert [x["full_name"] for x in items] == ["owner/repo-a", "owner/repo-b"]


def test_repo_files_requires_session(client: TestClient) -> None:
    response = client.get("/api/github/repos/owner/repo-a/files")
    assert response.status_code == 401
    assert response.json()["error"] == "UNAUTHORIZED"


def test_repo_files_success(
    client: TestClient,
    db_with_user: str,
) -> None:
    _set_session(client, {"user_id": "u1"})

    with patch(
        "src.api.github.github_repos.resolve_repo_owner_repo",
        new=AsyncMock(return_value=(None, "owner", "repo-a", "owner/repo-a")),
    ), patch(
        "src.api.github.github_repos.list_repo_files_tree",
        new=AsyncMock(
            return_value={
                "root": "/",
                "ref": None,
                "tree": [{"path": "src/", "type": "dir"}],
                "visited_nodes": 1,
            }
        ),
    ) as mock_list_repo_files_tree:
        response = client.get(
            "/api/github/repos/owner/repo-a/files",
            params={"path": "/"},
        )

    assert response.status_code == 200
    assert response.json()["repo_id"] == "owner/repo-a"
    assert response.json()["tree"][0]["path"] == "src/"
    assert mock_list_repo_files_tree.await_args.kwargs["depth"] == -1
    assert mock_list_repo_files_tree.await_args.kwargs["ref"] is None


def test_repo_contents_missing_path(
    client: TestClient,
    db_with_user: str,
) -> None:
    _set_session(client, {"user_id": "u1"})

    response = client.get("/api/github/repos/owner/repo-a/contents")
    assert response.status_code == 400
    assert response.json()["error"] == "BAD_REQUEST"


def test_repo_contents_raw_success(
    client: TestClient,
    db_with_user: str,
) -> None:
    _set_session(client, {"user_id": "u1"})

    with patch(
        "src.api.github.github_repos.resolve_repo_owner_repo",
        new=AsyncMock(return_value=(None, "owner", "repo-a", "owner/repo-a")),
    ), patch(
        "src.api.github.github_repos.get_repo_content",
        new=AsyncMock(return_value="hello world"),
    ):
        response = client.get(
            "/api/github/repos/owner/repo-a/contents",
            params={"path": "README.md", "encoding": "raw"},
        )

    assert response.status_code == 200
    assert response.text == "hello world"


def test_repo_commits_success(
    client: TestClient,
    db_with_user: str,
) -> None:
    _set_session(client, {"user_id": "u1"})

    fake_commits = {
        "repo_id": None,
        "ref": "main",
        "author": "testlogin",
        "summary": {
            "total_commits": 1,
            "author_commits": 1,
            "files_changed_total": 0,
            "date_range": {"from": "2026-01-01T00:00:00Z", "to": "2026-01-01T00:00:00Z"},
        },
        "commits": [
            {
                "sha": "abc",
                "message": "feat: x",
                "author": {"login": "testlogin", "name": "n", "email": "e"},
                "html_url": "https://github.com/owner/repo-a/commit/abc",
                "files_changed": 0,
                "date": "2026-01-01T00:00:00Z",
            }
        ],
        "page": 1,
        "per_page": 30,
    }

    with patch(
        "src.api.github.github_repos.resolve_repo_owner_repo",
        new=AsyncMock(return_value=(None, "owner", "repo-a", "owner/repo-a")),
    ), patch(
        "src.api.github.github_repos.list_repo_commits",
        new=AsyncMock(return_value=fake_commits),
    ):
        response = client.get("/api/github/repos/owner/repo-a/commits", params={"page": 1, "per_page": 30})

    assert response.status_code == 200
    body = response.json()
    assert body["author"] == "testlogin"
    assert body["repo_id"] == "owner/repo-a"

