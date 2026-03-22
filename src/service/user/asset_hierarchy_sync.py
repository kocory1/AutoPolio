"""
selected_repo_assets의 code 항목을 asset_hierarchy(code)에 반영 (데모·임베딩 SSoT).

임베딩 잡 완료 후 folder/project 행을 Chroma ``ids``와 맞추는 동기화도 제공한다.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.db.sqlite import connect
from src.service.github_embedding.paths import split_chroma_document_id
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


def _folder_project_rows_from_embedding_ids(
    repo_full_name: str,
    code_document_ids: list[str],
    result_ids: list[str],
) -> list[tuple[str, str]]:
    """
    ``result_ids``(Chroma id 목록)에서 folder·project만 골라 ``(id, type)`` 로 반환한다.

    code 경로는 ``code_document_ids``에서 분해한 상대 경로 집합으로 구분한다.
    """
    code_rels: set[str] = set()
    for doc_id in code_document_ids:
        r, rel = split_chroma_document_id(doc_id)
        if r == repo_full_name:
            code_rels.add(rel)

    rows: list[tuple[str, str]] = []
    for did in result_ids:
        r, rel = split_chroma_document_id(did)
        if r != repo_full_name:
            continue
        if rel == "/":
            rows.append((did, "project"))
        elif rel in code_rels:
            continue
        else:
            rows.append((did, "folder"))
    return rows


async def sync_folder_project_rows_from_embedding_result(
    *,
    user_id: str,
    repo_full_name: str,
    code_document_ids: list[str],
    result_ids: list[str],
    db_path: str | Path | None = None,
) -> None:
    """
    ``result_ids``에서 folder/project id만 추출한 뒤,
    해당 ``selected_repo``의 ``type IN ('folder','project')`` 행을 삭제하고 다시 INSERT 한다.
    """
    conn = await connect(db_path)
    try:
        cur = await conn.execute(
            """
            SELECT id FROM selected_repos
            WHERE user_id = ? AND repo_full_name = ?
            """,
            (user_id, repo_full_name),
        )
        row = await cur.fetchone()
        await cur.close()
        if not row:
            raise ValueError("SELECTED_REPO_NOT_FOUND")

        selected_repo_id = int(row["id"])

        await conn.execute(
            """
            DELETE FROM asset_hierarchy
            WHERE selected_repo_id = ? AND type IN ('folder', 'project')
            """,
            (selected_repo_id,),
        )

        for doc_id, htype in _folder_project_rows_from_embedding_ids(
            repo_full_name,
            code_document_ids,
            result_ids,
        ):
            await conn.execute(
                """
                INSERT INTO asset_hierarchy (id, selected_repo_id, type)
                VALUES (?, ?, ?)
                """,
                (doc_id, selected_repo_id, htype),
            )

        await conn.commit()
    finally:
        await conn.close()
