"""
FastAPI 앱 엔트리포인트.

라우터를 포함하고, 미들웨어·설정을 초기화한 app 인스턴스를 노출한다.
"""

from fastapi import FastAPI

from src.api import portfolio_router
from src.utils.langsmith import configure_langsmith


def create_app() -> FastAPI:
    """FastAPI 애플리케이션"""

    tracing_enabled = configure_langsmith(default_project="autofolio-dev")
    app = FastAPI(title="Autofolio API")
    app.state.langsmith_enabled = tracing_enabled

    app.include_router(portfolio_router)

    return app


app = create_app()
