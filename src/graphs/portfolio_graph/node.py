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

    재진입 시 consistency_feedback를 입력으로 받아 실패한 문장·구간만 보정 또는 피드백 반영 재생성.

    입력: profile, assets, (재진입 시) consistency_feedback
    출력: star (list)
    """
    # TODO: profile, assets로 STAR 문장 생성 (LLM 또는 규칙)
    # 재진입 시: state.get("consistency_feedback") 반영해 해당 문장만 재생성 또는 프롬프트에 지적 반영
    # star = generate_star_sentences(profile, assets, feedback=state.get("consistency_feedback"))
    # return {"star": star}
    return {
        "star": state.get("star") or [],
    }


def self_consistency(state: PortfolioState) -> dict:
    """환각 체크 + STAR 충실도 평가.

    실패 시 어디가 문제인지 구체적으로 consistency_feedback에 기록.

    입력: star, profile, assets
    출력: is_hallucination, is_star, (실패 시) consistency_feedback, star_retry_count 증가
    """
    # TODO: 환각 체크 — star 문장이 profile/assets에 근거하는지 검사
    # TODO: STAR 충실도 — 각 문장이 S/T/A/R 갖췄는지 평가
    # 실패 시: consistency_feedback = { "hallucination": [...], "star_fidelity": [...] }, star_retry_count += 1
    # 통과 시: is_hallucination=True, is_star=True 만 반환 (retry 변경 없음)
    return {
        "is_hallucination": True,
        "is_star": True,
        "consistency_feedback": state.get("consistency_feedback") or {},
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


def __fallback__(state: PortfolioState) -> dict:
    """재시도 상한 초과 시 호출. 플래그만 남기고 종료.

    실패 & star_retry_count >= max 시 여기로 라우팅.
    """
    # TODO: 필요 시 state에 error 또는 skip 플래그 설정
    # return {"error": "max_star_retries_exceeded"} 또는 그대로 반환
    return {}
