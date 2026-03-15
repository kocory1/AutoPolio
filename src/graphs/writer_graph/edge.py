"""2번 그래프(Writer) 조건 엣지 라우터.

검증 실패 시 consistency_feedback를 프롬프트에 담아 generate_draft 재호출.
"""

from .state import WriterState

MAX_DRAFT_RETRIES = 3


def after_retrieve_samples(state: WriterState) -> str:
    """retrieve_samples 이후 분기.

    - 통과 (error 없음) → load_assets
    - 검증 실패 (error 있음) → END
    """
    if state.get("error"):
        return "__end__"
    return "load_assets"


def after_load_assets(state: WriterState) -> str:
    """load_assets 이후 분기.

    - 통과 (error 없음) → generate_draft
    - 조회 실패 (error 있음) → END
    """
    if state.get("error"):
        return "__end__"
    return "generate_draft"


def after_self_consistency(state: WriterState) -> str:
    """self_consistency 이후 분기.

    - 통과 → format_output
    - 실패 & draft_retry_count < MAX → generate_draft (피드백 프롬프트 반영 재생성)
    - 실패 & draft_retry_count >= MAX → format_output (재시도 상한, 그대로 진행)
    """
    passed = state.get("is_hallucination")
    if passed:
        return "format_output"
    retry = state.get("draft_retry_count") or 0
    if retry < MAX_DRAFT_RETRIES:
        return "generate_draft"
    return "format_output"
