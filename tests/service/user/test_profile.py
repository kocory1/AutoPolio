"""service.user.profile 단위 테스트."""

from pathlib import Path

import pytest

from src.db.sqlite import connect, create_all_tables_async
from src.service.user import get_user_profile


@pytest.mark.asyncio
async def test_get_user_profile_returns_none_when_user_not_found(tmp_path: Path):
    db_path = tmp_path / "test.db"
    conn = await connect(db_path)
    try:
        await create_all_tables_async(conn)
    finally:
        await conn.close()

    result = await get_user_profile("missing-user", db_path=db_path)
    assert result is None


@pytest.mark.asyncio
async def test_get_user_profile_returns_profile_dict(tmp_path: Path):
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

    result = await get_user_profile("u1", db_path=db_path)
    assert result is not None
    assert result["id"] == "u1"
    assert result["github_username"] == "mspark"

