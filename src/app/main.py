"""
FastAPI 앱 엔트리포인트.

라우터를 포함하고, 미들웨어·설정을 초기화한 app 인스턴스를 노출한다.
"""

from fastapi import FastAPI


def create_app() -> FastAPI:
    """FastAPI 애플리케이션"""

    app = FastAPI(title="Autofolio API")

    # TODO: api 라우터(include_router)와 미들웨어를 여기에서 등록한다.

    return app


app = create_app()
