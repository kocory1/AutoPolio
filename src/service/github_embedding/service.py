"""
API·배치에서 호출하는 GitHub 임베딩 잡 (GitHub 원문 + Chroma).

``OPENAI_API_KEY``가 있으면 개발자 관점 LLM 요약 + OpenAI 임베딩을 사용하고,
없으면 결정적 스텁으로 동작한다(테스트·로컬 오프라인).
"""

from __future__ import annotations

import os

from src.service.git_hub import repos as github_repos
from src.service.github_embedding.chroma_store import GitHubEmbeddingChromaAdapter
from src.service.github_embedding.pipeline import (
    GitHubSummarizerPort,
    TextEmbedderPort,
    run_github_embedding_pipeline,
)


class _TokenGitHubContentAdapter:
    def __init__(self, access_token: str) -> None:
        self._access_token = access_token

    async def fetch_file(
        self,
        repo_full_name: str,
        path: str,
        ref: str | None,
    ) -> str:
        parts = repo_full_name.split("/", 1)
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise ValueError(f"invalid repo_full_name: {repo_full_name!r}")
        owner, repo = parts
        data = await github_repos.get_repo_content(
            self._access_token,
            owner=owner,
            repo=repo,
            path=path,
            ref=ref,
            encoding="raw",
        )
        return str(data)


class _DeterministicSummarizer:
    """LLM 없이 파이프라인·Chroma 적재를 검증하기 위한 결정적 요약."""

    async def summarize_file(
        self,
        repo_full_name: str,
        path: str,
        source_code: str,
    ) -> str:
        return f"FILE:{path}:{len(source_code)}"

    async def summarize_folder(
        self,
        repo_full_name: str,
        folder_path: str,
        child_summaries: list[str],
    ) -> str:
        joined = "|".join(child_summaries)
        return f"DIR:{folder_path}:{joined}"

    async def summarize_project(
        self,
        repo_full_name: str,
        root_child_summaries: list[str],
    ) -> str:
        return "PROJ:" + "|".join(root_child_summaries)


class _FixedDimEmbedder:
    def __init__(self, dim: int = 8) -> None:
        self._dim = dim

    async def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i, _ in enumerate(texts):
            base = (i + 1) * 0.01
            out.append([base + j * 0.001 for j in range(self._dim)])
        return out


def _default_summarizer_and_embedder(
) -> tuple[GitHubSummarizerPort, TextEmbedderPort]:
    if os.getenv("OPENAI_API_KEY"):
        from src.service.github_embedding.llm_summarizer import OpenAIDeveloperSummarizer
        from src.service.github_embedding.openai_embedder import OpenAIEmbedder

        return OpenAIDeveloperSummarizer(), OpenAIEmbedder()
    return _DeterministicSummarizer(), _FixedDimEmbedder()


async def run_github_repo_embedding_job(
    *,
    user_id: str,
    access_token: str,
    repo_full_name: str,
    code_document_ids: list[str],
    ref: str | None = None,
    chroma_persist_dir: str | None = None,
    summarizer: GitHubSummarizerPort | None = None,
    embedder: TextEmbedderPort | None = None,
    include_summaries: bool = False,
) -> dict[str, int | list[str] | list[dict[str, str]]]:
    """
    선택된 레포에 대해 code 문서 id 목록으로 임베딩 파이프라인을 실행한다.

    ``summarizer`` / ``embedder``를 생략하면 ``OPENAI_API_KEY`` 유무에 따라
    OpenAI 또는 스텁 구현을 고른다.
    """
    if (summarizer is None) ^ (embedder is None):
        raise ValueError("summarizer와 embedder는 둘 다 넘기거나 둘 다 생략해야 합니다.")

    if summarizer is None:
        summarizer, embedder = _default_summarizer_and_embedder()

    persist = chroma_persist_dir
    chroma = GitHubEmbeddingChromaAdapter(
        persist_dir=persist if persist is not None else None,
    )
    return await run_github_embedding_pipeline(
        user_id=user_id,
        repo_full_name=repo_full_name,
        code_document_ids=code_document_ids,
        ref=ref,
        content=_TokenGitHubContentAdapter(access_token),
        summarizer=summarizer,
        embedder=embedder,
        chroma=chroma,
        include_summaries=include_summaries,
    )
