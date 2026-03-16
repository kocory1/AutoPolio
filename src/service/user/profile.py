"""
유저 프로필 조회 서비스.

SQLite `users` 테이블을 조회해 그래프 노드에서 쓰기 쉬운 dict 형태로 반환한다.
"""

from __future__ import annotations

from pathlib import Path

from src.db.sqlite import connect


async def get_user_profile(user_id: str, db_path: str | Path | None = None) -> dict | None:
    """user_id로 users 테이블을 조회해 프로필을 반환한다.

    Returns:
        dict | None: 유저가 없으면 None.
    """
    conn = await connect(db_path)
    try:
        cursor = await conn.execute(
            """
            SELECT id, github_username, created_at, updated_at
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        )
        row = await cursor.fetchone()
        await cursor.close()
    finally:
        await conn.close()

    if row is None:
        return None

    return {
        "id": row["id"],
        "github_username": row["github_username"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }

