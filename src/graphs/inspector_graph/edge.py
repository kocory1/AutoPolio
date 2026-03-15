"""3번 그래프(Inspector) 조건 엣지 라우터.

load_draft 검증·조회 실패 시 END. re_inspect 후 round < max_rounds면 load_draft, 아니면 END.
"""

from .state import InspectorState

MAX_ROUNDS = 5


def after_load_draft(state: InspectorState) -> str:
    """load_draft 이후 분기.

    - 통과 (error 없음) → analyze
    - 검증·조회 실패 (error 있음) → END
    """
    if state.get("error"):
        return "__end__"
    return "analyze"


def after_re_inspect(state: InspectorState) -> str:
    """re_inspect 이후 분기.

    - user_edited 있음 & round < MAX_ROUNDS → load_draft (재첨삭 계속)
    - user_edited 없음 또는 round >= MAX_ROUNDS → END (재첨삭 종료)
    """
    user_edited = state.get("user_edited")
    round_val = state.get("round") or 0
    if not user_edited or round_val >= MAX_ROUNDS:
        return "__end__"
    return "load_draft"
