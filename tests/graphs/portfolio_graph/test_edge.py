"""portfolio_graph.edge 라우터 단위 테스트."""

from langgraph.graph import END

from src.graphs.portfolio_graph.edge import after_load_profile, after_self_consistency


def test_after_load_profile_routes_to_end_when_error_exists():
    assert after_load_profile({"error": "user_not_found"}) == END


def test_after_load_profile_routes_to_build_star_when_no_error():
    assert after_load_profile({"profile": {"id": "u1"}}) == "build_star_sentence"


def test_after_self_consistency_routes_to_build_portfolio_when_passed():
    assert (
        after_self_consistency(
            {
                "is_hallucination": False,
                "is_star": True,
                "star_retry_count": 0,
            }
        )
        == "build_portfolio"
    )


def test_after_self_consistency_retries_when_failed_and_retry_left():
    assert (
        after_self_consistency(
            {
                "is_hallucination": True,
                "is_star": True,
                "star_retry_count": 1,
            }
        )
        == "build_star_sentence"
    )


def test_after_self_consistency_routes_to_build_portfolio_when_retry_exhausted():
    assert (
        after_self_consistency(
            {
                "is_hallucination": False,
                "is_star": False,
                "star_retry_count": 3,
            }
        )
        == "build_portfolio"
    )

