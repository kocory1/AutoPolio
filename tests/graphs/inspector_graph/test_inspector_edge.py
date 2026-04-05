"""inspector_graph.edge 조건 분기 단위 테스트."""

from src.graphs.inspector_graph.edge import MAX_ROUNDS, after_load_draft, after_re_inspect


def test_after_load_draft_error_to_end():
    assert after_load_draft({"error": "x"}) == "__end__"


def test_after_load_draft_ok_to_analyze():
    assert after_load_draft({}) == "analyze"
    assert after_load_draft({"error": ""}) == "analyze"


def test_after_re_inspect_no_user_edited_to_end():
    assert after_re_inspect({"user_edited": "", "round": 0}) == "__end__"
    assert after_re_inspect({"user_edited": "   ", "round": 0}) == "__end__"


def test_after_re_inspect_with_edit_and_round_under_max():
    assert after_re_inspect({"user_edited": "수정", "round": 1}) == "load_draft"


def test_after_re_inspect_round_at_max_to_end():
    assert after_re_inspect({"user_edited": "수정", "round": MAX_ROUNDS}) == "__end__"
