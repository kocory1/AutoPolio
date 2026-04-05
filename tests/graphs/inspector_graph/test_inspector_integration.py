"""Inspector 그래프: checkpointer + interrupt_after + resume 시 load_draft 재진입."""

import pytest
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

import src.graphs.inspector_graph.graph as graph_module
from src.graphs.inspector_graph import node as node_module


@pytest.mark.asyncio
async def test_interrupt_after_suggest_then_resume_runs_load_draft_twice(monkeypatch):
    calls: list[str] = []

    async def fake_retrieve_user_assets(*_a, **_kw):
        return [{"id": "a1", "document": "에셋 요약", "metadata": {}, "distance": 0.1}]

    monkeypatch.setattr(
        "src.graphs.inspector_graph.node.retrieve_user_assets",
        fake_retrieve_user_assets,
    )

    async def tracking_load_draft(state):
        calls.append("load_draft")
        return await node_module.load_draft(state)

    async def tracking_analyze(state):
        calls.append("analyze")
        return {"suggestions": [{"section": "서론", "suggestion": "보완", "rationale": "테스트", "priority": "high"}]}

    async def tracking_suggest(state):
        calls.append("suggest")
        return await node_module.suggest(state)

    monkeypatch.setattr(graph_module, "load_draft", tracking_load_draft)
    monkeypatch.setattr(graph_module, "analyze", tracking_analyze)
    monkeypatch.setattr(graph_module, "suggest", tracking_suggest)

    memory = MemorySaver()
    app = graph_module.build_inspector_graph(memory)
    cfg = {"configurable": {"thread_id": "inspector-it-1"}}

    await app.ainvoke(
        {
            "user_id": "u1",
            "draft": "첫 초안",
            "question": "지원동기",
            "job_parsed": None,
        },
        cfg,
    )

    st = app.get_state(cfg)
    assert st.next == ("re_inspect",)
    assert calls == ["load_draft", "analyze", "suggest"]

    # interrupt 직후에는 dict 입력만으로는 다음 노드가 실행되지 않을 수 있음 → Command(update=...)
    await app.ainvoke(Command(update={"user_edited": "유저가 고친 초안"}), cfg)

    final = app.get_state(cfg)
    # 두 번째 사이클도 suggest 직후 다시 interrupt
    assert final.next == ("re_inspect",)
    assert final.values.get("draft") == "유저가 고친 초안"
    assert final.values.get("round") == 1
    assert calls.count("load_draft") == 2
    assert calls.count("analyze") == 2
    assert calls.count("suggest") == 2


@pytest.mark.asyncio
async def test_no_checkpointer_runs_suggest_then_re_inspect_noop_and_end(monkeypatch):
    calls: list[str] = []
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    async def fake_retrieve_user_assets(*_a, **_kw):
        return []

    monkeypatch.setattr(
        "src.graphs.inspector_graph.node.retrieve_user_assets",
        fake_retrieve_user_assets,
    )

    async def tracking_load_draft(state):
        calls.append("load_draft")
        return await node_module.load_draft(state)

    async def tracking_analyze(state):
        calls.append("analyze")
        return await node_module.analyze(state)

    async def tracking_suggest(state):
        calls.append("suggest")
        return await node_module.suggest(state)

    monkeypatch.setattr(graph_module, "load_draft", tracking_load_draft)
    monkeypatch.setattr(graph_module, "analyze", tracking_analyze)
    monkeypatch.setattr(graph_module, "suggest", tracking_suggest)

    app = graph_module.build_inspector_graph(None)
    result = await app.ainvoke(
        {
            "user_id": "u1",
            "draft": "초안",
            "question": "",
            "job_parsed": {},
            "user_edited": "",
        }
    )

    assert result.get("round") in (0, None)
    assert result.get("draft") == "초안"
    assert calls == ["load_draft", "analyze", "suggest"]
