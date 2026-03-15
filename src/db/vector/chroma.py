"""
ChromaDB 클라이언트 유틸.

유저별 User Asset 컬렉션(`user_assets_{user_id}`)을 조회/생성하는 공통 함수를 제공한다.
"""

from __future__ import annotations

import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv


def resolve_chroma_persist_dir() -> Path:
    """환경변수(`CHROMA_PERSIST_DIR`) 또는 기본값으로 persist 경로를 반환한다."""
    load_dotenv()
    persist_dir = os.getenv("CHROMA_PERSIST_DIR", "data/chroma")
    path = Path(persist_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_user_asset_collection_name(user_id: str) -> str:
    """문서 기준 컬렉션명(`user_assets_{user_id}`)을 반환한다."""
    return f"user_assets_{user_id}"


def get_chroma_client() -> chromadb.PersistentClient:
    """프로젝트 persist 경로 기반 Chroma PersistentClient를 생성한다."""
    return chromadb.PersistentClient(path=str(resolve_chroma_persist_dir()))


def get_user_asset_collection(user_id: str):
    """유저 에셋 컬렉션을 조회(없으면 생성)해 반환한다."""
    client = get_chroma_client()
    collection_name = build_user_asset_collection_name(user_id)
    return client.get_or_create_collection(name=collection_name)

