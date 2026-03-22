"""임베딩 파이프라인 포트 주입·목 검증."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.service.github_embedding.pipeline import run_github_embedding_pipeline


@pytest.mark.asyncio
async def test_pipeline_calls_delete_first_then_add_in_order() -> None:
    chroma = AsyncMock()

    async def _fetch(r: str, p: str, ref: str | None) -> str:
        return f"SRC({p})"

    content = MagicMock()
    content.fetch_file = AsyncMock(side_effect=_fetch)

    summarizer = AsyncMock()

    async def _sum_file(r: str, p: str, s: str) -> str:
        return f"SUMFILE({p})"

    async def _sum_dir(r: str, fp: str, ch: list[str]) -> str:
        return f"SUMDIR({fp}):{','.join(ch)}"

    async def _sum_proj(r: str, roots: list[str]) -> str:
        return f"SUMPROJ:{','.join(roots)}"

    summarizer.summarize_file.side_effect = _sum_file
    summarizer.summarize_folder.side_effect = _sum_dir
    summarizer.summarize_project.side_effect = _sum_proj

    async def _embed(texts: list[str]) -> list[list[float]]:
        return [[0.1, 0.2]] * len(texts)

    embedder = MagicMock()
    embedder.embed = AsyncMock(side_effect=_embed)

    repo = "owner/repo"
    ids = [f"{repo}/src/a.py", f"{repo}/src/b/c.py"]

    await run_github_embedding_pipeline(
        user_id="u1",
        repo_full_name=repo,
        code_document_ids=ids,
        ref="main",
        content=content,
        summarizer=summarizer,
        embedder=embedder,
        chroma=chroma,
    )

    chroma.delete_for_repo.assert_awaited_once_with("u1", repo)

    add_calls = chroma.add_documents.await_args_list
    assert len(add_calls) >= 3

    first_kw = add_calls[0].kwargs
    assert first_kw["ids"] == [f"{repo}/src/a.py"]
    assert first_kw["metadatas"][0]["type"] == "code"

    last_kw = add_calls[-1].kwargs
    assert last_kw["ids"] == [f"{repo}/"]
    assert last_kw["metadatas"][0]["type"] == "project"

    fetch_paths = [c.args[1] for c in content.fetch_file.await_args_list]
    assert fetch_paths == ["src/a.py", "src/b/c.py"]


@pytest.mark.asyncio
async def test_pipeline_rerun_deletes_before_add() -> None:
    chroma = AsyncMock()
    content = MagicMock()
    content.fetch_file = AsyncMock(return_value="x")
    summarizer = AsyncMock()
    summarizer.summarize_file.return_value = "s"
    summarizer.summarize_folder.return_value = "d"
    summarizer.summarize_project.return_value = "p"
    embedder = MagicMock()
    embedder.embed = AsyncMock(return_value=[[0.0]])

    repo = "o/r"
    doc_ids = [f"{repo}/f.py"]

    for _ in range(2):
        await run_github_embedding_pipeline(
            user_id="u",
            repo_full_name=repo,
            code_document_ids=doc_ids,
            ref=None,
            content=content,
            summarizer=summarizer,
            embedder=embedder,
            chroma=chroma,
        )

    assert chroma.delete_for_repo.await_count == 2
    # 루트 파일만 있으면 code 1 + project 1 = 2회 add / 런
    assert chroma.add_documents.await_count == 2 * 2


@pytest.mark.asyncio
async def test_pipeline_repo_mismatch_raises() -> None:
    chroma = AsyncMock()
    with pytest.raises(ValueError, match="mismatch"):
        c = MagicMock()
        c.fetch_file = AsyncMock()
        e = MagicMock()
        e.embed = AsyncMock()
        await run_github_embedding_pipeline(
            user_id="u",
            repo_full_name="a/b",
            code_document_ids=["c/d/x.py"],
            ref=None,
            content=c,
            summarizer=AsyncMock(),
            embedder=e,
            chroma=chroma,
        )


@pytest.mark.asyncio
async def test_pipeline_include_summaries_matches_ids() -> None:
    chroma = AsyncMock()
    content = MagicMock()
    content.fetch_file = AsyncMock(return_value="codebody")
    summarizer = AsyncMock()
    summarizer.summarize_file.return_value = "file_sum"
    summarizer.summarize_folder.return_value = "dir_sum"
    summarizer.summarize_project.return_value = "proj_sum"
    embedder = MagicMock()
    embedder.embed = AsyncMock(return_value=[[0.0]])

    repo = "o/r"
    ids_in = [f"{repo}/x.py"]
    out = await run_github_embedding_pipeline(
        user_id="u",
        repo_full_name=repo,
        code_document_ids=ids_in,
        ref=None,
        content=content,
        summarizer=summarizer,
        embedder=embedder,
        chroma=chroma,
        include_summaries=True,
    )
    assert "summaries" in out
    summ = out["summaries"]
    assert isinstance(summ, list)
    assert len(summ) == len(out["ids"])
    types = [r["type"] for r in summ]
    assert types == ["code", "project"]
    assert summ[0]["summary"] == "file_sum"
    assert summ[1]["summary"] == "proj_sum"
