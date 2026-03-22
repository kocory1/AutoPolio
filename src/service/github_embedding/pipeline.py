"""
GitHub 임베딩 파이프라인: content / LLM 요약 / 임베딩 / Chroma 저장 포트 주입.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.service.github_embedding.paths import (
    bottom_up_folder_order,
    collect_parent_directories,
    direct_children_for_folder,
    split_chroma_document_id,
)


@runtime_checkable
class GitHubContentPort(Protocol):
    async def fetch_file(
        self,
        repo_full_name: str,
        path: str,
        ref: str | None,
    ) -> str:
        """레포 내 파일 원문(또는 디코딩된 텍스트)을 반환한다."""


@runtime_checkable
class GitHubSummarizerPort(Protocol):
    async def summarize_file(
        self,
        repo_full_name: str,
        path: str,
        source_code: str,
    ) -> str:
        ...

    async def summarize_folder(
        self,
        repo_full_name: str,
        folder_path: str,
        child_summaries: list[str],
    ) -> str:
        ...

    async def summarize_project(
        self,
        repo_full_name: str,
        root_child_summaries: list[str],
    ) -> str:
        ...


@runtime_checkable
class TextEmbedderPort(Protocol):
    async def embed(self, texts: list[str]) -> list[list[float]]:
        ...


@runtime_checkable
class GitHubEmbeddingChromaPort(Protocol):
    async def delete_for_repo(self, user_id: str, repo_full_name: str) -> None:
        """해당 유저·레포 메타데이터를 가진 문서를 컬렉션에서 제거한다."""

    async def add_documents(
        self,
        *,
        user_id: str,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, str]],
        embeddings: list[list[float]],
    ) -> None:
        ...


def _normalize_metadata(
    user_id: str,
    repo_full_name: str,
    ref: str | None,
    asset_type: str,
    path_value: str,
) -> dict[str, str]:
    return {
        "user_id": user_id,
        "repo": repo_full_name,
        "ref": ref or "",
        "type": asset_type,
        "path": path_value,
    }


async def run_github_embedding_pipeline(
    *,
    user_id: str,
    repo_full_name: str,
    code_document_ids: list[str],
    ref: str | None,
    content: GitHubContentPort,
    summarizer: GitHubSummarizerPort,
    embedder: TextEmbedderPort,
    chroma: GitHubEmbeddingChromaPort,
    include_summaries: bool = False,
) -> dict[str, int | list[str] | list[dict[str, str]]]:
    """
    code 타입 Chroma id 목록을 받아 삭제→파일→폴더(bottom-up)→프로젝트 순으로 임베딩한다.

    Returns:
        ``embedded``, ``ids``. ``include_summaries=True``이면 ``summaries`` 키에
        ``[{id, type, path, summary}, ...]`` (Chroma에 넣은 문서 본문 = LLM 요약 등).
    """
    rel_paths: list[str] = []
    for doc_id in code_document_ids:
        r, rel = split_chroma_document_id(doc_id)
        if r != repo_full_name:
            raise ValueError(
                f"document id repo mismatch: expected {repo_full_name!r}, got {r!r} for {doc_id!r}"
            )
        if rel == "/":
            raise ValueError(f"code document id must not be project root: {doc_id!r}")
        rel_paths.append(rel)

    rel_paths_sorted = sorted(set(rel_paths))

    await chroma.delete_for_repo(user_id, repo_full_name)

    if not rel_paths_sorted:
        out: dict[str, int | list[str] | list[dict[str, str]]] = {"embedded": 0, "ids": []}
        if include_summaries:
            out["summaries"] = []
        return out

    summaries: dict[str, str] = {}
    saved_ids: list[str] = []

    for path in rel_paths_sorted:
        raw = await content.fetch_file(repo_full_name, path, ref)
        text = await summarizer.summarize_file(repo_full_name, path, raw)
        summaries[path] = text
        vectors = await embedder.embed([text])
        doc_id = f"{repo_full_name}/{path}"
        meta = _normalize_metadata(user_id, repo_full_name, ref, "code", path)
        await chroma.add_documents(
            user_id=user_id,
            ids=[doc_id],
            documents=[text],
            metadatas=[meta],
            embeddings=[vectors[0]],
        )
        saved_ids.append(doc_id)

    all_folders = collect_parent_directories(rel_paths_sorted)

    for folder in bottom_up_folder_order(rel_paths_sorted):
        child_keys = direct_children_for_folder(
            folder,
            file_paths=set(rel_paths_sorted),
            folder_paths=all_folders,
        )
        child_texts = [summaries[k] for k in child_keys]
        text = await summarizer.summarize_folder(repo_full_name, folder, child_texts)
        summaries[folder] = text
        vectors = await embedder.embed([text])
        doc_id = f"{repo_full_name}/{folder}"
        meta = _normalize_metadata(user_id, repo_full_name, ref, "folder", folder)
        await chroma.add_documents(
            user_id=user_id,
            ids=[doc_id],
            documents=[text],
            metadatas=[meta],
            embeddings=[vectors[0]],
        )
        saved_ids.append(doc_id)

    root_children = direct_children_for_folder(
        "",
        file_paths=set(rel_paths_sorted),
        folder_paths=all_folders,
    )
    root_texts = [summaries[k] for k in root_children]
    proj = await summarizer.summarize_project(repo_full_name, root_texts)
    vectors = await embedder.embed([proj])
    proj_id = f"{repo_full_name}/"
    proj_meta = _normalize_metadata(user_id, repo_full_name, ref, "project", "/")
    await chroma.add_documents(
        user_id=user_id,
        ids=[proj_id],
        documents=[proj],
        metadatas=[proj_meta],
        embeddings=[vectors[0]],
    )
    saved_ids.append(proj_id)

    result: dict[str, int | list[str] | list[dict[str, str]]] = {
        "embedded": len(saved_ids),
        "ids": saved_ids,
    }
    if include_summaries:
        code_path_set = set(rel_paths_sorted)
        rows: list[dict[str, str]] = []
        for did in saved_ids:
            _, rel = split_chroma_document_id(did)
            if rel == "/":
                rows.append(
                    {
                        "id": did,
                        "type": "project",
                        "path": "/",
                        "summary": proj,
                    }
                )
            elif rel in code_path_set:
                rows.append(
                    {
                        "id": did,
                        "type": "code",
                        "path": rel,
                        "summary": summaries[rel],
                    }
                )
            else:
                rows.append(
                    {
                        "id": did,
                        "type": "folder",
                        "path": rel,
                        "summary": summaries[rel],
                    }
                )
        result["summaries"] = rows
    return result
