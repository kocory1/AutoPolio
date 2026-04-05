"""re_inspect 노드 동작."""

from src.graphs.inspector_graph.node import re_inspect


def test_re_inspect_empty_user_edited_is_noop():
    assert re_inspect({"draft": "원문", "round": 0, "user_edited": ""}) == {}
    assert re_inspect({"draft": "원문", "round": 0, "user_edited": "  "}) == {}


def test_re_inspect_updates_draft_and_round():
    out = re_inspect({"draft": "원문", "round": 2, "user_edited": "편집됨"})
    assert out == {"draft": "편집됨", "round": 3}
