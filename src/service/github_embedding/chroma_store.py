"""
user_assets 컬렉션에 대한 레포 단위 삭제 및 문서 추가 (Chroma).
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import chromadb

from src.db.vector.chroma import (
    build_user_asset_collection_name,
    resolve_chroma_persist_dir,
)


def _collection_for_user(
    user_id: str,
    persist_dir: Path | str | None,
) -> Any:
    if persist_dir is not None:
        p = str(persist_dir)
    else:
        p = str(resolve_chroma_persist_dir())
    client = chromadb.PersistentClient(path=p)
    name = build_user_asset_collection_name(user_id)
    return client.get_or_create_collection(name=name)


def delete_docs_for_repo_sync(
    user_id: str,
    repo_full_name: str,
    *,
    persist_dir: Path | str | None = None,
) -> int:
    """
    ``user_id`` 컬렉션에서 ``repo`` 및 ``user_id`` 메타가 일치하는 문서를 삭제한다.

    Returns:
        삭제된 문서 수.
    """
    col = _collection_for_user(user_id, persist_dir)
    res = col.get(
        where={
            "$and": [
                {"user_id": {"$eq": user_id}},
                {"repo": {"$eq": repo_full_name}},
            ]
        },
    )
    ids = list(res.get("ids") or [])
    if ids:
        col.delete(ids=ids)
    return len(ids)


def add_documents_sync(
    user_id: str,
    *,
    ids: list[str],
    documents: list[str],
    metadatas: list[dict[str, str]],
    embeddings: list[list[float]],
    persist_dir: Path | str | None = None,
) -> None:
    col = _collection_for_user(user_id, persist_dir)
    col.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=embeddings,
    )


class GitHubEmbeddingChromaAdapter:
    """파이프라인용 비동기 래퍼. 테스트에서는 목으로 대체한다."""

    def __init__(self, persist_dir: Path | str | None = None) -> None:
        self._persist_dir = persist_dir

    async def delete_for_repo(self, user_id: str, repo_full_name: str) -> None:
        await asyncio.to_thread(
            delete_docs_for_repo_sync,
            user_id,
            repo_full_name,
            persist_dir=self._persist_dir,
        )

    async def add_documents(
        self,
        *,
        user_id: str,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, str]],
        embeddings: list[list[float]],
    ) -> None:
        await asyncio.to_thread(
            add_documents_sync,
            user_id,
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
            persist_dir=self._persist_dir,
        )
