"""service.user.repos 단위 테스트."""

from pathlib import Path

import pytest

from src.db.sqlite import connect, create_all_tables_async
from src.service.user import get_selected_repos


@pytest.mark.asyncio
async def test_get_selected_repos_returns_empty_when_none(tmp_path: Path):
    db_path = tmp_path / "test.db"
    conn = await connect(db_path)
    try:
        await create_all_tables_async(conn)
        await conn.execute(
            """
            INSERT INTO users (id, github_username, access_token, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("u1", "mspark", "token", "2026-03-01", "2026-03-01"),
        )
        await conn.commit()
    finally:
        await conn.close()

    result = await get_selected_repos("u1", db_path=db_path)
    assert result == []


@pytest.mark.asyncio
async def test_get_selected_repos_returns_repo_list(tmp_path: Path):
    db_path = tmp_path / "test.db"
    conn = await connect(db_path)
    try:
        await create_all_tables_async(conn)
        await conn.execute(
            """
            INSERT INTO users (id, github_username, access_token, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("u1", "mspark", "token", "2026-03-01", "2026-03-01"),
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
            ("u1", "owner/repo-b", "2026-03-02"),
        )
        await conn.commit()
    finally:
        await conn.close()

    result = await get_selected_repos("u1", db_path=db_path)
    assert result == ["owner/repo-a", "owner/repo-b"]

