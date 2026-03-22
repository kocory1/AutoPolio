"""
selected_repo_assets의 code 항목을 asset_hierarchy(code)에 반영 (데모·임베딩 SSoT).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.db.sqlite import connect
from src.service.user.selected_assets import get_selected_repo_assets


def _chroma_doc_id(repo_full_name: str, repo_path: str) -> str:
    rel = repo_path.strip().replace("\\", "/").strip("/")
    if not rel:
        raise ValueError(f"empty repo_path after normalize: {repo_path!r}")
    return f"{repo_full_name}/{rel}"


async def sync_code_rows_from_selected_assets(
    *,
    selected_repo_id: int,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """
    해당 ``selected_repo_id``의 ``type=code`` ``asset_hierarchy`` 행을 지우고,
    ``selected_repo_assets`` 중 ``asset_type=code``만 다시 넣는다.

    Returns:
        ``{"inserted": int, "ids": list[str]}``
    """
    conn = await connect(db_path)
    try:
        cur = await conn.execute(
            """
            SELECT repo_full_name
            FROM selected_repos
            WHERE id = ?
            """,
            (selected_repo_id,),
        )
        row = await cur.fetchone()
        await cur.close()
        if not row:
            raise ValueError("SELECTED_REPO_NOT_FOUND")

        full_name = str(row["repo_full_name"])
        assets = await get_selected_repo_assets(selected_repo_id, db_path=db_path)

        await conn.execute(
            """
            DELETE FROM asset_hierarchy
            WHERE selected_repo_id = ? AND type = 'code'
            """,
            (selected_repo_id,),
        )

        inserted_ids: list[str] = []
        for item in assets:
            if item.get("asset_type") != "code":
                continue
            rp = item.get("repo_path")
            if not isinstance(rp, str) or not rp.strip():
                continue
            doc_id = _chroma_doc_id(full_name, rp)
            await conn.execute(
                """
                INSERT INTO asset_hierarchy (id, selected_repo_id, type)
                VALUES (?, ?, 'code')
                """,
                (doc_id, selected_repo_id),
            )
            inserted_ids.append(doc_id)

        await conn.commit()
    finally:
        await conn.close()

    return {"inserted": len(inserted_ids), "ids": inserted_ids}
