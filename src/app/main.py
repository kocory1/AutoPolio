"""
FastAPI 앱 엔트리포인트.

라우터를 포함하고, 미들웨어·설정을 초기화한 app 인스턴스를 노출한다.
"""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from starlette.middleware.sessions import SessionMiddleware

from src.api import portfolio_router
from src.api.auth import router as auth_router
from src.api.github import router as github_router
from src.api.user_assets import router as user_assets_router
from src.db.sqlite import connect as sqlite_connect, create_all_tables_async
from src.web.dashboard import dashboard_html as dashboard_html_view
from src.utils.langsmith import configure_langsmith


def create_app() -> FastAPI:
    """FastAPI 애플리케이션"""

    tracing_enabled = configure_langsmith(default_project="autofolio-dev")
    app = FastAPI(
        title="Autofolio API",
        description="From Code to Career — 증거 기반 개발자 이력서 생성 서비스",
        version="1.0.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )
    app.state.langsmith_enabled = tracing_enabled

    app.add_middleware(
        SessionMiddleware,
        secret_key=os.getenv("SESSION_SECRET", "dev-secret"),
        https_only=False,
        same_site="lax",
        max_age=86400,
    )

    app.include_router(auth_router)
    app.include_router(portfolio_router)
    app.include_router(github_router)
    app.include_router(user_assets_router)

    # 런타임에서 DB 파일이 비어 있어도 바로 동작하도록 스키마를 초기화한다.
    @app.on_event("startup")
    async def _startup_init_db() -> None:
        conn = await sqlite_connect()
        try:
            await create_all_tables_async(conn)
        finally:
            await conn.close()

    @app.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        return HTMLResponse(dashboard_html_view)

    @app.get("/dashboard", response_class=HTMLResponse)
    async def dashboard() -> HTMLResponse:
        return HTMLResponse(dashboard_html_view)

    return app


app = create_app()
