"""3번 그래프(Inspector) 노드. 내부 로직은 TODO 주석으로만 표시."""

from .state import InspectorState


def load_draft(state: InspectorState) -> dict:
    """진입 시 검증 + 무조건 에셋·합격 샘플 재조회.

    입력: draft, user_edited, user_id, question, job_parsed (API에서 전달)
    출력: (통과) assets, samples / (검증·조회 실패) error → END
    """
    # TODO: draft 없고 user_edited도 없으면 error 설정 후 반환
    # TODO: user_edited 있으면 draft = user_edited, round += 1
    # TODO: Writer load_assets와 동일 모듈로 user_id + question + job_parsed → 에셋 조회
    # TODO: Writer retrieve_passed_cover_letters와 동일 모듈로 question + job_parsed → 합격 샘플 검색
    # TODO: 조회 실패 시 error 설정 후 반환
    return {
        "assets": state.get("assets") or [],
        "samples": state.get("samples") or [],
    }


def analyze(state: InspectorState) -> dict:
    """LLM 보완점 분석 → suggestions 직접 출력.

    입력: draft, assets, samples, user_edited, round
    출력: suggestions (list of dict: 구간, 제안 내용, 근거, 우선순위 등)
    """
    # TODO: draft + assets 요약 + samples 예시(일부)로 LLM 프롬프트 구성
    # TODO: 재첨삭 시(round > 0) "이전 라운드 제안 반영 후 수정된 초안" 프롬프트 추가
    # TODO: suggestions = llm.invoke(...) → 구조화된 제안 목록
    return {"suggestions": state.get("suggestions") or []}


def suggest(state: InspectorState) -> dict:
    """제안 반환. interrupt 지점.

    입력: suggestions
    출력: suggestions (API 응답에 그대로 사용)
    """
    # TODO: suggestions 그대로 전달. interrupt_after로 Human 대기
    return {"suggestions": state.get("suggestions") or []}


def re_inspect(state: InspectorState) -> dict:
    """재호출 시 user_edited → draft 갱신, round 증가.

    입력: user_edited, round
    출력: draft, round
    """
    # TODO: draft = user_edited
    # TODO: round += 1
    user_edited = state.get("user_edited") or ""
    current_round = state.get("round") or 0
    return {
        "draft": user_edited,
        "round": current_round + 1,
    }
