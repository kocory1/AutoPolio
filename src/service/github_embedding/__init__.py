"""
GitHub 코드·폴더·프로젝트 임베딩 파이프라인 (Chroma user_assets).

순수 경로 유틸, 포트 주입 가능한 오케스트레이션, Chroma 저장소 헬퍼를 제공한다.
"""

from __future__ import annotations

from src.service.github_embedding.hierarchy import fetch_code_document_ids_for_repo
from src.service.github_embedding.paths import (
    bottom_up_folder_order,
    collect_parent_directories,
    split_chroma_document_id,
)
from src.service.github_embedding.pipeline import (
    GitHubContentPort,
    GitHubEmbeddingChromaPort,
    GitHubSummarizerPort,
    TextEmbedderPort,
    run_github_embedding_pipeline,
)

__all__ = [
    "GitHubContentPort",
    "GitHubEmbeddingChromaPort",
    "GitHubSummarizerPort",
    "TextEmbedderPort",
    "bottom_up_folder_order",
    "collect_parent_directories",
    "fetch_code_document_ids_for_repo",
    "run_github_embedding_pipeline",
    "split_chroma_document_id",
]
