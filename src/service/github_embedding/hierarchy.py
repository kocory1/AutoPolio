"""
SQLite asset_hierarchy에서 임베딩 대상 code 문서 id 조회.
"""

from __future__ import annotations

from pathlib import Path

from src.db.sqlite.client import connect


async def fetch_code_document_ids_for_repo(
    user_id: str,
    repo_full_name: str,
    db_path: str | Path | None = None,
) -> list[str]:
    """
    ``selected_repos``와 조인해 해당 유저·레포의 ``type='code'`` 행 ``id``만 반환한다.

    ``id``는 ``owner/repo/...`` 형태(Chroma document id / Contents 경로 SSoT).
    """
    conn = await connect(db_path)
    try:
        cursor = await conn.execute(
            """
            SELECT ah.id
            FROM asset_hierarchy AS ah
            INNER JOIN selected_repos AS sr ON sr.id = ah.selected_repo_id
            WHERE sr.user_id = ?
              AND sr.repo_full_name = ?
              AND ah.type = 'code'
            ORDER BY ah.id ASC
            """,
            (user_id, repo_full_name),
        )
        rows = await cursor.fetchall()
        await cursor.close()
    finally:
        await conn.close()

    return [str(row["id"]) for row in rows]
