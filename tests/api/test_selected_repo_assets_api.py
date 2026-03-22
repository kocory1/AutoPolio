from __future__ import annotations

import asyncio
import json
import os
from base64 import b64encode
from typing import Any, Dict

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


def _set_session(client: TestClient, data: Dict[str, Any]) -> None:
    """
    SessionMiddleware가 읽는 signed cookie 포맷과 동일하게 session 쿠키를 만든다.
    """
    secret_key = os.getenv("SESSION_SECRET", "dev-secret")
    payload = b64encode(json.dumps(data).encode("utf-8"))
    signed = TimestampSigner(secret_key).sign(payload).decode("utf-8")
    client.cookies.set("session", signed, path="/")


@pytest.fixture
def db_with_selected_repos(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> dict:
    """
    - users: u1, u2
    - selected_repos:
        - u1 -> owner/repo-a
        - u2 -> owner/repo-b
    """
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("SQLITE_DB_PATH", str(db_path))

    async def setup() -> dict:
        conn = await connect(db_path)
        try:
            await create_all_tables_async(conn)

            await conn.execute(
                """
                INSERT INTO users (id, github_username, access_token, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("u1", "user1", "token1", "2026-03-01", "2026-03-01"),
            )
            await conn.execute(
                """
                INSERT INTO users (id, github_username, access_token, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                ("u2", "user2", "token2", "2026-03-01", "2026-03-01"),
            )

            await conn.execute(
                """
                INSERT INTO selected_repos (user_id, repo_full_name, created_at)
                VALUES (?, ?, ?)
                """,
                ("u1", "owner/repo-a", "2026-03-01"),
            )
            await conn.execute(
                """
                INSERT INTO selected_repos (user_id, repo_full_name, created_at)
                VALUES (?, ?, ?)
                """,
                ("u2", "owner/repo-b", "2026-03-01"),
            )
            await conn.commit()

            cur = await conn.execute(
                """
                SELECT id
                FROM selected_repos
                WHERE user_id = ? AND repo_full_name = ?
                """,
                ("u1", "owner/repo-a"),
            )
            row = await cur.fetchone()
            u1_selected_repo_id = row["id"]

            cur2 = await conn.execute(
                """
                SELECT id
                FROM selected_repos
                WHERE user_id = ? AND repo_full_name = ?
                """,
                ("u2", "owner/repo-b"),
            )
            row2 = await cur2.fetchone()
            u2_selected_repo_id = row2["id"]

            return {
                "db_path": str(db_path),
                "u1_selected_repo_id": u1_selected_repo_id,
                "u2_selected_repo_id": u2_selected_repo_id,
            }
        finally:
            await conn.close()

    return _run(setup())


@pytest.fixture
def client(db_with_selected_repos: dict) -> TestClient:
    # DB env는 db_with_selected_repos fixture에서 세팅되므로, 반드시 그 후에 client 생성
    return TestClient(app)


def test_selected_repo_assets_requires_session(client: TestClient) -> None:
    response = client.get(
        "/api/user/selected-repo-assets",
        params={"selected_repo_id": 1},
    )
    assert response.status_code == 401
    assert response.json() == {
        "error": "UNAUTHORIZED",
        "message": "UNAUTHORIZED",
    }

    response2 = client.put(
        "/api/user/selected-repo-assets",
        json={"selected_repo_id": 1, "assets": []},
    )
    assert response2.status_code == 401
    assert response2.json() == {
        "error": "UNAUTHORIZED",
        "message": "UNAUTHORIZED",
    }


def test_selected_repo_assets_get_requires_selected_repo_id(
    client: TestClient,
) -> None:
    _set_session(client, {"user_id": "u1"})
    response = client.get("/api/user/selected-repo-assets")
    assert response.status_code == 400
    assert response.json() == {
        "error": "BAD_REQUEST",
        "message": "selected_repo_id is required",
    }


def test_selected_repo_assets_forbidden_when_wrong_user(
    client: TestClient,
    db_with_selected_repos: dict,
) -> None:
    _set_session(client, {"user_id": "u1"})

    response = client.get(
        "/api/user/selected-repo-assets",
        params={"selected_repo_id": db_with_selected_repos["u2_selected_repo_id"]},
    )
    assert response.status_code == 403
    assert response.json() == {
        "error": "FORBIDDEN",
        "message": "SELECTED_REPO_NOT_FOUND",
    }


def test_selected_repo_assets_put_and_get_roundtrip(
    client: TestClient,
    db_with_selected_repos: dict,
) -> None:
    _set_session(client, {"user_id": "u1"})

    selected_repo_id = db_with_selected_repos["u1_selected_repo_id"]

    assets = [
        {"asset_type": "folder", "repo_path": "src"},
        {"asset_type": "code", "repo_path": "src/app/main.py"},
        # 중복: 실제 저장은 중복 제거되며, retrieval은 ORDER BY로 정렬됨
        {"asset_type": "code", "repo_path": "src/app/main.py"},
    ]

    response = client.put(
        "/api/user/selected-repo-assets",
        json={"selected_repo_id": selected_repo_id, "assets": assets},
    )
    assert response.status_code == 200

    response2 = client.get(
        "/api/user/selected-repo-assets",
        params={"selected_repo_id": selected_repo_id},
    )
    assert response2.status_code == 200

    items = response2.json()["selected_repo_assets"]
    # ORDER BY asset_type ASC, repo_path ASC 이므로 code -> folder 순
    assert items == [
        {"asset_type": "code", "repo_path": "src/app/main.py"},
        {"asset_type": "folder", "repo_path": "src"},
    ]

