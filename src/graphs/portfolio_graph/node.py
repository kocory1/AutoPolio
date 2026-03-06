"""1번 그래프(포트폴리오 생성) 노드. 내부 로직은 주석으로만 표시."""

from .state import PortfolioState


def load_profile(state: PortfolioState) -> dict:
    """User 프로필·에셋 로드 (P1 API 또는 DB).

    입력: state["user_id"]
    출력: profile, assets
    """
    # TODO: user_id로 프로필·에셋 조회 API/DB 호출
    # profile = fetch_profile(state["user_id"])
    # assets = fetch_assets(state["user_id"])
    # return {"profile": profile, "assets": assets}
    return {
        "profile": state.get("profile") or {},
        "assets": state.get("assets") or [],
    }


def build_star_sentence(state: PortfolioState) -> dict:
    """프로필·에셋 → STAR 성과 문장 후보 생성.

    재진입 시 consistency_feedback를 프롬프트에 담아 수정 반영 재생성.

    입력: profile, assets, (재진입 시) consistency_feedback
    출력: star (list)
    """
    # TODO: profile, assets로 STAR 문장 생성 (LLM 또는 규칙)
    # 재진입 시: state.get("consistency_feedback")를 프롬프트에 포함
    #   예: "다음 지적을 반영해 수정: {consistency_feedback}"
    # star = generate_star_sentences(profile, assets, feedback=state.get("consistency_feedback"))
    feedback = state.get("consistency_feedback") or {}

    # 스텁: 재진입(피드백 있음) 시 플레이스홀더 반환 → self_consistency 통과
    if feedback and (state.get("assets") or state.get("profile")):
        return {"star": [{"situation": "(프로필 기반)", "task": "(에셋 기반)", "action": "(수정 반영)", "result": "(결과)"}]}

    return {"star": state.get("star") or []}


def self_consistency(state: PortfolioState) -> dict:
    """환각 체크 + STAR 충실도 평가.

    실패 시 consistency_feedback 기록, star_retry_count 증가 → build_star_sentence 재호출.
    LangGraph 활용 핵심: 검증 실패 시 피드백을 프롬프트에 반영해 재생성 루프.

    입력: star, profile, assets, star_retry_count
    출력: is_hallucination, is_star, (실패 시) consistency_feedback, star_retry_count+1
    """
    star = state.get("star") or []
    retry_count = state.get("star_retry_count") or 0

    # TODO: 환각 체크 — star 문장이 profile/assets에 근거하는지 LLM 검사
    # TODO: STAR 충실도 — 각 문장이 S/T/A/R 갖췄는지 평가
    # 현재: star 비어있으면 실패 (실제 검증 로직 구현 시 교체)
    is_hallucination = True
    is_star = True
    consistency_feedback: dict = {}

    if not star:
        is_hallucination = False
        is_star = False
        consistency_feedback = {
            "hallucination": [{"reason": "STAR 문장이 없습니다. 프로필·에셋 기반으로 생성해 주세요."}],
            "star_fidelity": [],
        }
        retry_count += 1

    return {
        "is_hallucination": is_hallucination,
        "is_star": is_star,
        "consistency_feedback": consistency_feedback,
        "star_retry_count": retry_count,
    }


def build_portfolio(state: PortfolioState) -> dict:
    """검증된 STAR·프로필·에셋 → 포트폴리오.

    입력: star, profile, assets
    출력: portfolio
    """
    # TODO: star, profile, assets로 포트폴리오(웹 페이지 또는 구조화 데이터) 생성
    # portfolio = render_portfolio(star, profile, assets)
    # return {"portfolio": portfolio}
    return {
        "portfolio": state.get("portfolio") or {},
    }
