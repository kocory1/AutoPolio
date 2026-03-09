"""2번 그래프(Writer) State 정의."""

from typing import TypedDict


class WriterState(TypedDict, total=False):
    """Writer 그래프 State.

    - user_id: 사용자 식별자 (load_assets에서 유저 DB 조회용)
    - assets: 매칭된 에셋 목록 (load_assets 출력)
    - question: 자소서 문항 (질문 텍스트)
    - max_chars: 글자수 제한. 유저 입력 (draft API 요청 시 필수)
    - job_parsed: 채용 공고 파싱 결과 (기업명, 인재상 등)
    - samples: 합격 자소서 검색 모듈 결과 (retrieve_samples 출력)
    - draft: LLM 초안 (generate_draft 출력, format_output에서 정제)
    - is_hallucination: self_consistency 환각 체크 통과 여부
    - draft_retry_count: generate_draft 재진입 횟수 (피드백 반영 재생성)
    - consistency_feedback: 검증 실패 시 재생성용 피드백 (프롬프트에 반영)
    - messages: (선택) 대화 이력 — 스트리밍/디버깅용
    - error: 에러 메시지 — retrieve_samples·load_assets 검증/조회 실패 시
    """

    user_id: str
    assets: list
    question: str
    max_chars: int
    job_parsed: dict
    samples: list
    draft: str
    is_hallucination: bool
    draft_retry_count: int
    consistency_feedback: dict
    messages: list
    error: str
