"""3번 그래프(Inspector) State.

docs/AUTOFOLIO_Inspector_그래프_파이프라인_제안.md §3 기준.
"""

from typing import TypedDict


class InspectorState(TypedDict, total=False):
    """Inspector 그래프 State.

    - user_id: 에셋 조회용 (API/invoke 주입)
    - question: 직무·문항 맥락 (analyze 프롬프트·향후 RAG 쿼리)
    - job_parsed: 공고/직무 파싱 결과 (향후 합격 샘플 RAG)
    - draft: 초안 (Writer 출력 또는 이전 라운드 user_edited)
    - assets: 에셋 목록 (load_draft에서 무조건 재조회)
    - samples: 합격 자소서 목록 (load_draft에서 무조건 재조회)
    - suggestions: 보완 제안 목록 (analyze 출력, suggest 반환)
    - user_edited: 유저가 수정한 초안 (재호출 시 draft로 사용)
    - round: 재첨삭 라운드 (0=최초, 1+=재첨삭; re_inspect에서만 증가)
    - error: 검증/조회 실패 시 에러 메시지
    """

    user_id: str
    question: str
    job_parsed: dict | None

    draft: str
    assets: list
    samples: list
    suggestions: list
    user_edited: str
    round: int
    error: str
