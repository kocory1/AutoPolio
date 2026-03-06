"""1번 그래프(포트폴리오 생성) State 정의."""

from typing import TypedDict


class PortfolioState(TypedDict, total=False):
    """포트폴리오 생성 그래프 State.

    - user_id: 사용자 식별자
    - profile: User 프로필 (load_profile 출력)
    - assets: 에셋 목록 (load_profile 출력)
    - star: STAR 성과 문장 목록 (build_star_sentence 출력)
    - is_hallucination: self_consistency 환각 체크 통과 여부
    - is_star: self_consistency STAR 충실도 통과 여부
    - star_retry_count: build_star_sentence 재진입 횟수 (피드백 반영 재생성)
    - portfolio: 최종 포트폴리오 (build_portfolio 출력)
    - consistency_feedback: 검증 실패 시 재생성용 피드백 (프롬프트에 반영)
    """

    user_id: str
    profile: dict
    assets: list
    star: list
    is_hallucination: bool
    is_star: bool
    star_retry_count: int
    portfolio: dict | str
    consistency_feedback: dict
