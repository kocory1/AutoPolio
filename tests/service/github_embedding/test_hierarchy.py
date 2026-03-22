"""asset_hierarchy code id 조회."""

from __future__ import annotations

import asyncio

from src.db.sqlite import connect, create_all_tables_async
from src.service.github_embedding.hierarchy import fetch_code_document_ids_for_repo


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def test_fetch_code_document_ids_for_repo_ordered(tmp_path) -> None:
    db = tmp_path / "t.db"

    async def setup() -> list[str]:
        conn = await connect(db)
        await create_all_tables_async(conn)
        await conn.execute(
            """
            INSERT INTO users (id, github_username, access_token, created_at, updated_at)
            VALUES ('u1', 'x', 'tok', '2026-01-01', '2026-01-01')
            """,
        )
        await conn.execute(
            """
            INSERT INTO selected_repos (user_id, repo_full_name, created_at)
            VALUES ('u1', 'o/r', '2026-01-01')
            """,
        )
        cur = await conn.execute(
            "SELECT id FROM selected_repos WHERE user_id = ? AND repo_full_name = ?",
            ("u1", "o/r"),
        )
        sr_id = (await cur.fetchone())["id"]
        await cur.close()
        await conn.execute(
            """
            INSERT INTO asset_hierarchy (id, selected_repo_id, type)
            VALUES ('o/r/b.py', ?, 'code')
            """,
            (sr_id,),
        )
        await conn.execute(
            """
            INSERT INTO asset_hierarchy (id, selected_repo_id, type)
            VALUES ('o/r/a.py', ?, 'code')
            """,
            (sr_id,),
        )
        await conn.commit()
        await conn.close()
        return await fetch_code_document_ids_for_repo("u1", "o/r", db_path=db)

    assert _run(setup()) == ["o/r/a.py", "o/r/b.py"]


def test_fetch_code_empty_when_no_rows(tmp_path) -> None:
    db = tmp_path / "e.db"

    async def setup() -> None:
        conn = await connect(db)
        await create_all_tables_async(conn)
        await conn.execute(
            """
            INSERT INTO users (id, github_username, access_token, created_at, updated_at)
            VALUES ('u1', 'x', 'tok', '2026-01-01', '2026-01-01')
            """,
        )
        await conn.execute(
            """
            INSERT INTO selected_repos (user_id, repo_full_name, created_at)
            VALUES ('u1', 'o/r', '2026-01-01')
            """,
        )
        await conn.commit()
        await conn.close()

    _run(setup())

    async def load() -> list[str]:
        return await fetch_code_document_ids_for_repo("u1", "o/r", db_path=db)

    assert _run(load()) == []
