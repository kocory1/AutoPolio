"""2번 그래프(Writer) 조립."""

from pathlib import Path

from langgraph.graph import END, START, StateGraph

from src.utils.visualize import save_graph_png

from .edge import after_load_assets, after_retrieve_samples, after_self_consistency
from .node import format_output, generate_draft, load_assets, retrieve_samples, self_consistency
from .state import WriterState


def build_writer_graph():
    """Writer 그래프 조립.

    플로우:
      START → retrieve_samples → (통과) load_assets → (통과) generate_draft → self_consistency
        → (통과 또는 retry >= 3) format_output → END
        → (실패 & retry < 3) generate_draft (피드백 프롬프트 반영 재생성)
      retrieve_samples·load_assets 검증/조회 실패 시 → END
    """
    graph = StateGraph(WriterState)

    graph.add_node("retrieve_samples", retrieve_samples)
    graph.add_node("load_assets", load_assets)
    graph.add_node("generate_draft", generate_draft)
    graph.add_node("self_consistency", self_consistency)
    graph.add_node("format_output", format_output)

    graph.add_edge(START, "retrieve_samples")
    graph.add_conditional_edges(
        "retrieve_samples",
        after_retrieve_samples,
        {"load_assets": "load_assets", "__end__": END},
    )
    graph.add_conditional_edges(
        "load_assets",
        after_load_assets,
        {"generate_draft": "generate_draft", "__end__": END},
    )
    graph.add_edge("generate_draft", "self_consistency")
    graph.add_conditional_edges(
        "self_consistency",
        after_self_consistency,
        {
            "format_output": "format_output",
            "generate_draft": "generate_draft",
        },
    )
    graph.add_edge("format_output", END)

    return graph.compile()


if __name__ == "__main__":
    # 프로젝트 루트에서 실행: python -m src.graphs.writer_graph.graph
    compiled = build_writer_graph()
    save_graph_png(compiled, Path("docs/writer_graph.png"))
