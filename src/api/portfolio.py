"""
포트폴리오 API 라우터.

selected_repos(SSoT) 기반으로 포트폴리오를 생성하고 저장/조회한다.
"""

from __future__ import annotations

import aiosqlite
from fastapi import APIRouter, Header, Query
from fastapi.responses import JSONResponse

from src.graphs.portfolio_graph import build_portfolio_graph
from src.service.portfolio import create_portfolio, get_portfolio_by_id, list_portfolios

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


def _error_response(status_code: int, error: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": error,
            "message": message,
        },
    )


def _map_graph_error(raw_error: str) -> tuple[int, str, str]:
    if raw_error == "user_not_found":
        return 404, "NOT_FOUND", "USER_NOT_FOUND"
    if raw_error == "no_selected_repos":
        return 400, "BAD_REQUEST", "NO_SELECTED_REPOS"
    if raw_error == "user_id is required":
        return 400, "BAD_REQUEST", "USER_ID_REQUIRED"
    if raw_error.startswith("build_star_sentence_failed"):
        return 500, "INTERNAL_SERVER_ERROR", "BUILD_STAR_SENTENCE_FAILED"
    if raw_error.startswith("load_profile_failed"):
        return 500, "INTERNAL_SERVER_ERROR", "LOAD_PROFILE_FAILED"
    return 500, "INTERNAL_SERVER_ERROR", "PORTFOLIO_GRAPH_FAILED"


@router.post("/generate")
async def generate_portfolio(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    """포트폴리오 생성 그래프를 실행하고 결과를 저장한다."""
    if not x_user_id:
        return _error_response(401, "UNAUTHORIZED", "UNAUTHORIZED")

    graph = build_portfolio_graph()
    result = await graph.ainvoke({"user_id": x_user_id})

    graph_error = result.get("error")
    if graph_error:
        status_code, error, message = _map_graph_error(graph_error)
        return _error_response(status_code, error, message)

    portfolio = result.get("portfolio")
    if not isinstance(portfolio, dict):
        return _error_response(500, "INTERNAL_SERVER_ERROR", "INVALID_PORTFOLIO_RESULT")

    try:
        saved = await create_portfolio(
            user_id=x_user_id,
            content=portfolio,
        )
    except aiosqlite.Error:
        return _error_response(500, "INTERNAL_SERVER_ERROR", "PORTFOLIO_PERSIST_FAILED")

    return {
        "portfolio_id": saved["portfolio_id"],
        "user_id": x_user_id,
        "portfolio": portfolio,
        "created_at": saved["created_at"],
    }


@router.get("")
async def get_portfolio(
    portfolio_id: str | None = Query(default=None),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    """포트폴리오 목록 또는 단건을 조회한다."""
    if not x_user_id:
        return _error_response(401, "UNAUTHORIZED", "UNAUTHORIZED")

    if portfolio_id:
        item = await get_portfolio_by_id(x_user_id, portfolio_id)
        if item is None:
            return _error_response(404, "NOT_FOUND", "PORTFOLIO_NOT_FOUND")
        return item

    items = await list_portfolios(x_user_id)
    return {"items": items}

