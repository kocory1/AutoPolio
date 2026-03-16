"""1번 그래프(포트폴리오 생성) State 정의."""

from typing import TypedDict


class PortfolioState(TypedDict, total=False):
    """포트폴리오 생성 그래프 State.

    - user_id: 사용자 식별자
    - profile: User 프로필 (load_profile 출력)
    - assets: 에셋 목록 (load_profile 출력)
    - selected_repos: 유저가 선택한 레포 목록 (load_profile 출력)
    - repo_assets_map: 레포별 에셋 맵 (load_profile 출력)
    - project_candidates: 레포별 STAR 후보 묶음 (build_star_sentence 출력)
    - repo_errors: 레포별 STAR 생성 실패 사유 (부분 실패 시)
    - is_hallucination: self_consistency 환각 존재 여부 (True=환각 있음, False=환각 없음)
    - is_star: self_consistency STAR 충실도 통과 여부
    - star_retry_count: build_star_sentence 재진입 횟수 (피드백 반영 재생성)
    - portfolio: 최종 포트폴리오 (build_portfolio 출력)
    - consistency_feedback: 검증 실패 시 재생성용 피드백 (프롬프트에 반영)
    - error: 노드 실행 실패/검증 실패 메시지
    """

    user_id: str
    profile: dict
    assets: list
    selected_repos: list[str]
    repo_assets_map: dict[str, list]
    project_candidates: list
    repo_errors: dict[str, str]
    is_hallucination: bool
    is_star: bool
    star_retry_count: int
    portfolio: dict | str
    consistency_feedback: dict
    error: str
