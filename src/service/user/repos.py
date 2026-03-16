"""
유저 선택 레포 조회 서비스.

SQLite `selected_repos` 테이블에서 user_id 기준 레포 목록을 반환한다.
"""

from __future__ import annotations

from pathlib import Path

from src.db.sqlite import connect


async def get_selected_repos(user_id: str, db_path: str | Path | None = None) -> list[str]:
    """user_id의 selected_repos.repo_full_name 목록을 반환한다."""
    conn = await connect(db_path)
    try:
        cursor = await conn.execute(
            """
            SELECT repo_full_name
            FROM selected_repos
            WHERE user_id = ?
            ORDER BY id ASC
            """,
            (user_id,),
        )
        rows = await cursor.fetchall()
        await cursor.close()
    finally:
        await conn.close()

    return [row["repo_full_name"] for row in rows]

