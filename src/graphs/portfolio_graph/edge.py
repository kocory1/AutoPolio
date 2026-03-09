"""1번 그래프(포트폴리오 생성) 조건 엣지 라우터.

검증 실패 시 consistency_feedback를 프롬프트에 담아 build_star_sentence 재호출.
"""

from .state import PortfolioState

MAX_STAR_RETRIES = 3


def after_self_consistency(state: PortfolioState) -> str:
    """self_consistency 이후 분기.

    - 통과 → build_portfolio
    - 실패 & star_retry_count < MAX → build_star_sentence (피드백 프롬프트에 반영해 재생성)
    - 실패 & star_retry_count >= MAX → build_portfolio (재시도 상한, 그대로 진행)
    """
    passed = state.get("is_hallucination") and state.get("is_star")
    if passed:
        return "build_portfolio"
    retry = state.get("star_retry_count") or 0
    if retry < MAX_STAR_RETRIES:
        return "build_star_sentence"
    return "build_portfolio"
