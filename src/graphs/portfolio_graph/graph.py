"""1번 그래프(포트폴리오 생성) 조립."""

from pathlib import Path

from langgraph.graph import END, START, StateGraph

from .edge import after_self_consistency
from .node import (
    build_portfolio,
    build_star_sentence,
    load_profile,
    self_consistency,
)
from .state import PortfolioState


def build_portfolio_graph():
    """포트폴리오 생성 그래프 조립.

    플로우:
      START → load_profile → build_star_sentence → self_consistency
        → (통과) build_portfolio → END
        → (실패 & retry < 3) build_star_sentence (피드백 프롬프트 반영 재생성)
        → (실패 & retry >= 3) build_portfolio → END
    """
    graph = StateGraph(PortfolioState)

    graph.add_node("load_profile", load_profile)
    graph.add_node("build_star_sentence", build_star_sentence)
    graph.add_node("self_consistency", self_consistency)
    graph.add_node("build_portfolio", build_portfolio)

    graph.add_edge(START, "load_profile")
    graph.add_edge("load_profile", "build_star_sentence")
    graph.add_edge("build_star_sentence", "self_consistency")
    graph.add_conditional_edges(
        "self_consistency",
        after_self_consistency,
        {
            "build_portfolio": "build_portfolio",
            "build_star_sentence": "build_star_sentence",
        },
    )
    graph.add_edge("build_portfolio", END)

    return graph.compile()


if __name__ == "__main__":
    # 프로젝트 루트에서 실행: python -m src.graphs.portfolio_graph.graph
    # 컴파일된 그래프를 PNG로 저장 (노드 아님, main 전용)
    compiled = build_portfolio_graph()
    out_png = Path("docs/portfolio_graph.png")
    out_png.parent.mkdir(parents=True, exist_ok=True)
    try:
        compiled.get_graph().draw_mermaid_png(output_file_path=str(out_png))
        print("PNG written to", out_png)
    except Exception as e:
        print("PNG export failed (network required for Mermaid.ink API):", e)
