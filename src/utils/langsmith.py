"""
LangSmith tracing 초기화 유틸.

환경변수를 기반으로 LangGraph/LangChain 실행 추적을 활성화한다.
"""

from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    def load_dotenv(*args, **kwargs):  # type: ignore[override]
        return False


def configure_langsmith(default_project: str = "autofolio-dev") -> bool:
    """LangSmith tracing 환경을 설정하고 활성화 여부를 반환한다.

    필수: LANGSMITH_API_KEY
    선택: LANGSMITH_PROJECT, LANGSMITH_TRACING, LANGSMITH_ENDPOINT
    """

    # 프로젝트 루트(.env) 우선 로드
    load_dotenv(dotenv_path=Path(".env"), override=False)

    api_key = os.getenv("LANGSMITH_API_KEY")
    if not api_key:
        return False

    os.environ.setdefault("LANGSMITH_TRACING", "true")
    os.environ.setdefault("LANGSMITH_PROJECT", default_project)
    os.environ.setdefault("LANGSMITH_ENDPOINT", "https://api.smith.langchain.com")

    return os.getenv("LANGSMITH_TRACING", "").lower() == "true"

