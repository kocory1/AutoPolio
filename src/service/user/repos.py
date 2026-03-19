"""
유저 선택 레포 조회 서비스.

SQLite `selected_repos` 테이블에서 user_id 기준 레포 목록을 반환한다.
"""

from __future__ import annotations

from datetime import datetime, timezone
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


async def get_selected_repos_detailed(
    user_id: str,
    db_path: str | Path | None = None,
) -> list[dict]:
    """selected_repos를 [{id, full_name}, ...] 형태로 반환한다."""
    conn = await connect(db_path)
    try:
        cursor = await conn.execute(
            """
            SELECT id, repo_full_name
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

    return [{"id": row["id"], "full_name": row["repo_full_name"]} for row in rows]


async def upsert_selected_repos(
    *,
    user_id: str,
    repo_full_names: list[str],
    replace: bool = True,
    created_at: str | None = None,
    db_path: str | Path | None = None,
) -> list[dict]:
    """
    selected_repos를 갱신한다.

    - replace=True: 기존 목록 삭제 후 전체 재삽입
    - replace=False: 기존 목록에 병합(중복은 무시)
    """
    if created_at is None:
        created_at = datetime.now(timezone.utc).isoformat()

    unique_full_names = []
    seen = set()
    for n in repo_full_names:
        if not n:
            continue
        if n in seen:
            continue
        seen.add(n)
        unique_full_names.append(n)

    conn = await connect(db_path)
    try:
        if replace:
            await conn.execute("DELETE FROM selected_repos WHERE user_id = ?", (user_id,))

        # UNIQUE(user_id, repo_full_name) 제약을 활용해 중복 삽입을 무시한다.
        for full_name in unique_full_names:
            await conn.execute(
                """
                INSERT OR IGNORE INTO selected_repos (user_id, repo_full_name, created_at)
                VALUES (?, ?, ?)
                """,
                (user_id, full_name, created_at),
            )

        await conn.commit()
    finally:
        await conn.close()

    return await get_selected_repos_detailed(user_id, db_path=db_path)

