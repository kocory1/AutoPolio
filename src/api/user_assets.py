from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.db.sqlite.client import connect
from src.service.user.selected_assets import (
    get_selected_repo_assets,
    replace_selected_repo_assets,
)


router = APIRouter(prefix="/api/user", tags=["UserAssets"])


def _error_response(status_code: int, error: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": error, "message": message})


async def _require_user_id(request: Request) -> str:
    user_id = request.session.get("user_id")
    if not user_id:
        raise ValueError("UNAUTHORIZED")
    return str(user_id)


async def _require_selected_repo_belongs_to_user(
    *,
    conn,
    selected_repo_id: int,
    user_id: str,
) -> None:
    cursor = await conn.execute(
        """
        SELECT id
        FROM selected_repos
        WHERE id = ?
          AND user_id = ?
        """,
        (selected_repo_id, user_id),
    )
    row = await cursor.fetchone()
    await cursor.close()
    if not row:
        raise ValueError("FORBIDDEN:selected_repo_not_found")


@router.get("/selected-repo-assets", response_model=None)
async def selected_repo_assets_get(
    request: Request,
    selected_repo_id: int | None = None,
) -> JSONResponse:
    try:
        user_id = await _require_user_id(request)
    except ValueError:
        return _error_response(401, "UNAUTHORIZED", "UNAUTHORIZED")

    if not selected_repo_id:
        return _error_response(400, "BAD_REQUEST", "selected_repo_id is required")

    conn = await connect()
    try:
        try:
            await _require_selected_repo_belongs_to_user(
                conn=conn,
                selected_repo_id=selected_repo_id,
                user_id=user_id,
            )
        except ValueError:
            return _error_response(403, "FORBIDDEN", "SELECTED_REPO_NOT_FOUND")

        items = await get_selected_repo_assets(selected_repo_id, db_path=None)
        return JSONResponse({"selected_repo_assets": items})
    finally:
        await conn.close()


@router.put("/selected-repo-assets", response_model=None)
async def selected_repo_assets_put(
    request: Request,
) -> JSONResponse:
    try:
        user_id = await _require_user_id(request)
    except ValueError:
        return _error_response(401, "UNAUTHORIZED", "UNAUTHORIZED")

    body = await request.json()
    selected_repo_id = body.get("selected_repo_id")
    assets: List[Dict[str, Any]] = body.get("assets") or []

    if not selected_repo_id:
        return _error_response(400, "BAD_REQUEST", "selected_repo_id is required")
    if not isinstance(assets, list) or len(assets) == 0:
        return _error_response(400, "BAD_REQUEST", "assets must be a non-empty array")

    try:
        selected_repo_id_int = int(selected_repo_id)
    except Exception:
        return _error_response(400, "BAD_REQUEST", "selected_repo_id must be integer")

    conn = await connect()
    try:
        try:
            await _require_selected_repo_belongs_to_user(
                conn=conn,
                selected_repo_id=selected_repo_id_int,
                user_id=user_id,
            )
        except ValueError:
            return _error_response(403, "FORBIDDEN", "SELECTED_REPO_NOT_FOUND")

        saved = await replace_selected_repo_assets(
            selected_repo_id_int,
            items=assets,
            db_path=None,
        )
        return JSONResponse({"selected_repo_assets": saved})
    finally:
        await conn.close()

