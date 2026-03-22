"""asset_hierarchy folder/project 동기화 (임베딩 result ids)."""

from __future__ import annotations

import asyncio

from src.db.sqlite import connect, create_all_tables_async
from src.service.user.asset_hierarchy_sync import sync_folder_project_rows_from_embedding_result


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def test_sync_folder_project_replaces_rows(tmp_path) -> None:
    db = tmp_path / "t.db"

    async def setup() -> int:
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
        sr_id = int((await cur.fetchone())["id"])
        await cur.close()
        await conn.execute(
            """
            INSERT INTO asset_hierarchy (id, selected_repo_id, type)
            VALUES ('o/r/a.py', ?, 'code')
            """,
            (sr_id,),
        )
        await conn.execute(
            """
            INSERT INTO asset_hierarchy (id, selected_repo_id, type)
            VALUES ('o/r/old', ?, 'folder')
            """,
            (sr_id,),
        )
        await conn.commit()
        await conn.close()
        return sr_id

    sr_id = _run(setup())

    result_ids = ["o/r/a.py", "o/r/src", "o/r/"]

    async def sync() -> None:
        await sync_folder_project_rows_from_embedding_result(
            user_id="u1",
            repo_full_name="o/r",
            code_document_ids=["o/r/a.py"],
            result_ids=result_ids,
            db_path=db,
        )

    _run(sync())

    async def verify() -> list[tuple[str, str]]:
        conn = await connect(db)
        try:
            cur = await conn.execute(
                """
                SELECT id, type FROM asset_hierarchy
                WHERE selected_repo_id = ?
                ORDER BY type ASC, id ASC
                """,
                (sr_id,),
            )
            rows = await cur.fetchall()
            await cur.close()
        finally:
            await conn.close()
        return [(str(r["id"]), str(r["type"])) for r in rows]

    assert _run(verify()) == [
        ("o/r/a.py", "code"),
        ("o/r/src", "folder"),
        ("o/r/", "project"),
    ]


def test_sync_folder_project_empty_result_deletes_only_folder_project(tmp_path) -> None:
    db = tmp_path / "e.db"

    async def setup() -> int:
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
        sr_id = int((await cur.fetchone())["id"])
        await cur.close()
        await conn.execute(
            """
            INSERT INTO asset_hierarchy (id, selected_repo_id, type)
            VALUES ('o/r/x.py', ?, 'code')
            """,
            (sr_id,),
        )
        await conn.execute(
            """
            INSERT INTO asset_hierarchy (id, selected_repo_id, type)
            VALUES ('o/r/legacy', ?, 'folder')
            """,
            (sr_id,),
        )
        await conn.commit()
        await conn.close()
        return sr_id

    sr_id = _run(setup())

    async def sync() -> None:
        await sync_folder_project_rows_from_embedding_result(
            user_id="u1",
            repo_full_name="o/r",
            code_document_ids=[],
            result_ids=[],
            db_path=db,
        )

    _run(sync())

    async def verify() -> list[tuple[str, str]]:
        conn = await connect(db)
        try:
            cur = await conn.execute(
                """
                SELECT id, type FROM asset_hierarchy
                WHERE selected_repo_id = ?
                ORDER BY id ASC
                """,
                (sr_id,),
            )
            rows = await cur.fetchall()
            await cur.close()
        finally:
            await conn.close()
        return [(str(r["id"]), str(r["type"])) for r in rows]

    assert _run(verify()) == [("o/r/x.py", "code")]
