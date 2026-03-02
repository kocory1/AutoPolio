"""1번 그래프(포트폴리오 생성) 조건 엣지 라우터."""

from .state import PortfolioState

# 재진입 상한: 이 횟수 초과 시 build_star_sentence 대신 __fallback__ 또는 build_portfolio로 진행
MAX_STAR_RETRIES = 3


def after_self_consistency(
    state: PortfolioState,
) -> str:
    """self_consistency 이후 분기.

    - 통과(is_hallucination & is_star) → build_portfolio
    - 실패 & star_retry_count < MAX → build_star_sentence (피드백 반영 재생성)
    - 실패 & star_retry_count >= MAX → __fallback__
    """
    passed = state.get("is_hallucination") and state.get("is_star")
    if passed:
        return "build_portfolio"
    retry = state.get("star_retry_count") or 0
    if retry < MAX_STAR_RETRIES:
        return "build_star_sentence"
    return "__fallback__"
