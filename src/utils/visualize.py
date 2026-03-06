"""그래프 시각화 유틸 (CompiledStateGraph → PNG / ASCII)."""

import random
from dataclasses import dataclass
from pathlib import Path

from langgraph.graph.state import CompiledStateGraph


@dataclass
class NodeStyles:
    default: str = (
        "fill:#45C4B0, fill-opacity:0.3, color:#23260F, stroke:#45C4B0, stroke-width:1px, font-weight:bold, line-height:1.2"  # 기본 색상
    )
    first: str = (
        "fill:#45C4B0, fill-opacity:0.1, color:#23260F, stroke:#45C4B0, stroke-width:1px, font-weight:normal, font-style:italic, stroke-dasharray:2,2"  # 점선 테두리
    )
    last: str = (
        "fill:#45C4B0, fill-opacity:1, color:#000000, stroke:#45C4B0, stroke-width:1px, font-weight:normal, font-style:italic, stroke-dasharray:2,2"  # 점선 테두리
    )


def visualize_graph(graph, xray=False, ascii=False):
    """
    CompiledStateGraph 객체를 시각화하여 표시합니다.
    Jupyter 환경에서 IPython.display 사용. 그 외에는 ASCII 출력.

    Args:
        graph: 시각화할 그래프 객체. CompiledStateGraph 인스턴스여야 합니다.
        xray: 그래프 내부 상태를 표시할지 여부.
        ascii: ASCII 형식으로 그래프를 표시할지 여부.
    """
    if not ascii:
        try:
            from IPython.display import Image, display

            if isinstance(graph, CompiledStateGraph):
                display(
                    Image(
                        graph.get_graph(xray=xray).draw_mermaid_png(
                            background_color="white",
                            node_colors=NodeStyles(),
                        )
                    )
                )
        except ImportError:
            print(graph.get_graph(xray=xray).draw_ascii())
        except Exception as e:
            print(f"그래프 시각화 실패: {e}")
            try:
                print(graph.get_graph(xray=xray).draw_ascii())
            except Exception as ascii_error:
                print(f"ASCII 표시도 실패: {ascii_error}")
    else:
        print(graph.get_graph(xray=xray).draw_ascii())


def save_graph_png(graph, output_path: str | Path, xray: bool = False) -> bool:
    """CompiledStateGraph를 PNG 파일로 저장.

    Args:
        graph: CompiledStateGraph 인스턴스
        output_path: 저장 경로 (str 또는 Path)
        xray: 그래프 내부 상태 표시 여부

    Returns:
        성공 시 True, 실패 시 False
    """
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if isinstance(graph, CompiledStateGraph):
            graph.get_graph(xray=xray).draw_mermaid_png(
                output_file_path=str(path),
                background_color="white",
                node_colors=NodeStyles(),
            )
            print("PNG written to", path)
            return True
    except Exception as e:
        print(f"PNG export failed (network required for Mermaid.ink API): {e}")
        try:
            print(graph.get_graph(xray=xray).draw_ascii())
        except Exception as ascii_error:
            print(f"ASCII 표시도 실패: {ascii_error}")
    return False


def generate_random_hash():
    return f"{random.randint(0, 0xFFFFFF):06x}"
