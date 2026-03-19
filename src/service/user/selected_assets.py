"""
유저가 선택한 레포 내부 assets(폴더/파일) 저장/조회 서비스.

이 데이터는 임베딩 API의 paths 선택 기준으로 재사용될 수 있다.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from src.db.sqlite import connect


def _normalize_asset_type(asset_type: object) -> str | None:
    if asset_type not in {"code", "folder"}:
        return None
    return str(asset_type)


def _normalize_repo_path(repo_path: object) -> str | None:
    if not isinstance(repo_path, str):
        return None
    repo_path = repo_path.strip()
    if not repo_path:
        return None
    return repo_path


async def get_selected_repo_assets(
    selected_repo_id: int,
    db_path: str | Path | None = None,
) -> list[dict]:
    """selected_repo_assets를 [{asset_type, repo_path}, ...] 형태로 반환한다."""
    conn = await connect(db_path)
    try:
        cursor = await conn.execute(
            """
            SELECT asset_type, repo_path
            FROM selected_repo_assets
            WHERE selected_repo_id = ?
            ORDER BY asset_type ASC, repo_path ASC
            """,
            (selected_repo_id,),
        )
        rows = await cursor.fetchall()
        await cursor.close()
    finally:
        await conn.close()

    return [{"asset_type": row["asset_type"], "repo_path": row["repo_path"]} for row in rows]


async def replace_selected_repo_assets(
    selected_repo_id: int,
    *,
    items: list[dict],
    db_path: str | Path | None = None,
) -> list[dict]:
    """selected_repo_assets를 assets 목록으로 완전 교체한 뒤 저장 결과를 반환한다."""
    now = datetime.now(timezone.utc).isoformat()

    normalized: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for item in items:
        if not isinstance(item, dict):
            continue
        asset_type = _normalize_asset_type(item.get("asset_type"))
        repo_path = _normalize_repo_path(item.get("repo_path"))
        if not asset_type or not repo_path:
            continue
        key = (asset_type, repo_path)
        if key in seen:
            continue
        seen.add(key)
        normalized.append(key)

    conn = await connect(db_path)
    try:
        await conn.execute(
            "DELETE FROM selected_repo_assets WHERE selected_repo_id = ?",
            (selected_repo_id,),
        )
        for asset_type, repo_path in normalized:
            await conn.execute(
                """
                INSERT OR IGNORE INTO selected_repo_assets
                  (selected_repo_id, asset_type, repo_path, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (selected_repo_id, asset_type, repo_path, now),
            )
        await conn.commit()
    finally:
        await conn.close()

    return await get_selected_repo_assets(selected_repo_id, db_path=db_path)

