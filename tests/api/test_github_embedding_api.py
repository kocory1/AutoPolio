"""POST /api/github/repos/{repo_id}/embedding — 세션·선택 레포·서비스 패치."""

from __future__ import annotations

import asyncio
import json
import os
from base64 import b64encode
from typing import Any, Dict
from unittest.mock import AsyncMock, patch

import pytest
from itsdangerous import TimestampSigner
from starlette.testclient import TestClient

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
def db_with_user_and_selected(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
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
        await conn.execute(
            """
            INSERT INTO selected_repos (user_id, repo_full_name, created_at)
            VALUES (?, ?, ?)
            """,
            ("u1", "owner/repo-a", "2026-03-01"),
        )
        await conn.commit()
        await conn.close()

    _run(setup())


def _set_session(client: TestClient, data: Dict[str, Any]) -> None:
    secret_key = os.getenv("SESSION_SECRET", "dev-secret")
    payload = b64encode(json.dumps(data).encode("utf-8"))
    signed = TimestampSigner(secret_key).sign(payload).decode("utf-8")
    client.cookies.set("session", signed, path="/")


def test_github_embedding_requires_session(client: TestClient) -> None:
    r = client.post(
        "/api/github/repos/owner%2Frepo-a/embedding",
        json={"code_document_ids": []},
    )
    assert r.status_code == 401
    assert r.json()["error"] == "UNAUTHORIZED"


def test_github_embedding_forbidden_when_not_selected(
    client: TestClient,
    db_with_user_and_selected: None,
) -> None:
    _set_session(client, {"user_id": "u1"})
    r = client.post(
        "/api/github/repos/other%2Fnot-selected/embedding",
        json={"code_document_ids": ["other/not-selected/x.py"]},
    )
    assert r.status_code == 403
    assert r.json()["error"] == "FORBIDDEN"


def test_github_embedding_bad_repo_id(client: TestClient, db_with_user_and_selected: None) -> None:
    _set_session(client, {"user_id": "u1"})
    r = client.post(
        "/api/github/repos/not-a-slash/embedding",
        json={"code_document_ids": []},
    )
    assert r.status_code == 400
    assert r.json()["error"] == "BAD_REQUEST"


def test_github_embedding_no_code_in_hierarchy(
    client: TestClient,
    db_with_user_and_selected: None,
) -> None:
    _set_session(client, {"user_id": "u1"})
    r = client.post(
        "/api/github/repos/owner%2Frepo-a/embedding",
        json={"code_document_ids": []},
    )
    assert r.status_code == 400
    assert r.json()["message"] == "NO_CODE_ASSETS_IN_HIERARCHY"


def test_github_embedding_loads_ids_from_hierarchy(
    client: TestClient,
    db_with_user_and_selected: None,
) -> None:
    db_path = os.environ.get("SQLITE_DB_PATH", "")

    async def insert_code_row() -> None:
        conn = await connect(db_path)
        cur = await conn.execute(
            """
            SELECT id FROM selected_repos
            WHERE user_id = ? AND repo_full_name = ?
            """,
            ("u1", "owner/repo-a"),
        )
        row = await cur.fetchone()
        await cur.close()
        assert row is not None
        sr_id = row["id"]
        await conn.execute(
            """
            INSERT INTO asset_hierarchy (id, selected_repo_id, type)
            VALUES (?, ?, 'code')
            """,
            ("owner/repo-a/lib/hi.py", sr_id),
        )
        await conn.commit()
        await conn.close()

    _run(insert_code_row())

    _set_session(client, {"user_id": "u1"})

    fake = {"embedded": 3, "ids": ["owner/repo-a/lib/hi.py", "owner/repo-a/"]}

    with patch(
        "src.api.github.run_github_repo_embedding_job",
        new=AsyncMock(return_value=fake),
    ) as job:
        r = client.post(
            "/api/github/repos/owner%2Frepo-a/embedding",
            json={"code_document_ids": []},
        )

    assert r.status_code == 200
    job.assert_awaited_once()
    kwargs = job.await_args.kwargs
    assert kwargs["code_document_ids"] == ["owner/repo-a/lib/hi.py"]


def test_github_embedding_success_patched_service(
    client: TestClient,
    db_with_user_and_selected: None,
) -> None:
    _set_session(client, {"user_id": "u1"})
    fake = {"embedded": 2, "ids": ["owner/repo-a/a.py", "owner/repo-a/"]}

    with patch(
        "src.api.github.run_github_repo_embedding_job",
        new=AsyncMock(return_value=fake),
    ) as job:
        r = client.post(
            "/api/github/repos/owner%2Frepo-a/embedding",
            json={"code_document_ids": ["owner/repo-a/a.py"], "ref": "main"},
        )

    job.assert_awaited_once()
    assert r.status_code == 200
    body = r.json()
    assert body["embedded"] == 2
    assert body["ids"] == fake["ids"]
