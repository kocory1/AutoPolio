"""3번 그래프(Inspector) 조립.

Human-in-the-loop: suggest 노드 이후 interrupt_after. checkpointer 필요.
"""

from pathlib import Path
from typing import Any

from langgraph.graph import END, START, StateGraph

from src.utils.visualize import save_graph_png

from .edge import after_load_draft, after_re_inspect
from .node import analyze, load_draft, re_inspect, suggest
from .state import InspectorState


def build_inspector_graph(checkpointer: Any = None):
    """Inspector 그래프 조립.

    플로우:
      START → load_draft → (통과) analyze → suggest ──(interrupt)──→ [Human 대기]
        → (재호출) re_inspect → (round < max) load_draft → ... / (round >= max) END
      load_draft 검증·조회 실패 시 → END

    Args:
        checkpointer: Human-in-the-loop용. None이면 interrupt_after 미적용(시각화용).
    """
    graph = StateGraph(InspectorState)

    graph.add_node("load_draft", load_draft)
    graph.add_node("analyze", analyze)
    graph.add_node("suggest", suggest)
    graph.add_node("re_inspect", re_inspect)

    graph.add_edge(START, "load_draft")
    graph.add_conditional_edges(
        "load_draft",
        after_load_draft,
        {"analyze": "analyze", "__end__": END},
    )
    graph.add_edge("analyze", "suggest")
    graph.add_edge("suggest", "re_inspect")
    graph.add_conditional_edges(
        "re_inspect",
        after_re_inspect,
        {"load_draft": "load_draft", "__end__": END},
    )

    compile_kwargs: dict = {}
    if checkpointer is not None:
        compile_kwargs["checkpointer"] = checkpointer
        compile_kwargs["interrupt_after"] = ["suggest"]

    return graph.compile(**compile_kwargs)


if __name__ == "__main__":
    # 프로젝트 루트에서 실행: python -m src.graphs.inspector_graph.graph
    # checkpointer 없이 시각화 (interrupt 미적용)
    compiled = build_inspector_graph()
    save_graph_png(compiled, Path("docs/inspector_graph.png"))
