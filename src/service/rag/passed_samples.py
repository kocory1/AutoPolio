"""
합격 자소서(문항 단위) ChromaDB 조회.

스키마: docs/AUTOFOLIO_합격자소서_벡터DB_스키마.md
컬렉션: `passed_cover_letters` (없거나 비어 있으면 빈 리스트).

적재 시 OpenAI 임베딩을 쓴 경우 검색도 동일 모델로 `query_embeddings`를 사용한다.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from src.db.vector.chroma import get_chroma_client

PASSED_COVER_LETTERS_COLLECTION = "passed_cover_letters"


def _strip_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    s = value.strip()
    return s if s else None


def _format_year_for_query(y: str) -> str:
    """'2022' 또는 '2022년 상반기' 등 — 문장 안에서 '년' 중복 방지."""
    y = (y or "").strip()
    if not y:
        return ""
    if "년" in y:
        return y
    return f"{y}년"


def _build_query_text(
    question: str,
    company_name: str | None,
    position: str | None,
    year: str | None,
) -> str:
    """임베딩 쿼리 문자열. company/position/year가 모두 있을 때만 전체 포맷."""
    q = (question or "").strip()
    c = _strip_or_none(company_name)
    p = _strip_or_none(position)
    y_raw = _strip_or_none(year)
    y_fmt = _format_year_for_query(y_raw) if y_raw else ""
    if c and p and y_fmt:
        return f"{c}의 {y_fmt} {p} 공고의 자기소개서 문항 1 : {q}"
    return f"자기소개서 문항 1 : {q}"


def _build_where_clause(
    company_name: str | None,
    position: str | None,
    year: str | None,
) -> dict[str, Any] | None:
    """company·position·year 세 값이 모두 있을 때만 $and 필터. 아니면 None (유사도만)."""
    c = _strip_or_none(company_name)
    p = _strip_or_none(position)
    y = _strip_or_none(year)
    if c is None or p is None or y is None:
        return None
    return {
        "$and": [
            {"company": {"$eq": c}},
            {"position": {"$eq": p}},
            {"year": {"$eq": y}},
        ],
    }


def _normalize_passed_results(raw: dict[str, Any]) -> list[dict[str, Any]]:
    """Chroma query 결과를 Writer용 dict 리스트로 변환."""
    ids = (raw.get("ids") or [[]])[0]
    metas = (raw.get("metadatas") or [[]])[0]
    dists = (raw.get("distances") or [[]])[0]

    out: list[dict[str, Any]] = []
    for idx, _ in enumerate(ids):
        meta = metas[idx] if idx < len(metas) else None
        if not isinstance(meta, dict):
            meta = {}

        def _meta_str(key: str) -> str:
            v = meta.get(key)
            if v is None:
                return ""
            return str(v)

        dist = dists[idx] if idx < len(dists) else None
        out.append(
            {
                "question": _meta_str("question"),
                "answer": _meta_str("answer"),
                "company": _meta_str("company"),
                "position": _meta_str("position"),
                "year": _meta_str("year"),
                "source": _meta_str("source"),
                "distance": dist,
            }
        )
    return out


def _get_collection_if_nonempty():
    try:
        client = get_chroma_client()
        collection = client.get_collection(name=PASSED_COVER_LETTERS_COLLECTION)
        if collection.count() == 0:
            return None
        return collection
    except Exception:
        return None


def _query_passed_with_text_sync(
    collection,
    query_text: str,
    n_results: int,
    where: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    kwargs: dict[str, Any] = {
        "query_texts": [query_text],
        "n_results": n_results,
    }
    if where is not None:
        kwargs["where"] = where
    try:
        raw = collection.query(**kwargs)
    except Exception:
        return []
    return _normalize_passed_results(raw)


def _query_passed_with_embedding_sync(
    collection,
    query_embedding: list[float],
    n_results: int,
    where: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    kwargs: dict[str, Any] = {
        "query_embeddings": [query_embedding],
        "n_results": n_results,
    }
    if where is not None:
        kwargs["where"] = where
    try:
        raw = collection.query(**kwargs)
    except Exception:
        return []
    return _normalize_passed_results(raw)


async def retrieve_passed_cover_letters(
    question: str,
    company_name: str | None = None,
    position: str | None = None,
    year: str | None = None,
    top_k: int = 5,
) -> list[dict]:
    """합격 자소서 문항 청크를 유사도 검색한다.

    - 쿼리 텍스트는 스키마와 동일한 포맷(또는 메타 미완 시 축약 포맷)으로 구성한다.
    - ``company`` / ``position`` / ``year``가 **모두** 있을 때만 메타 ``$and`` 필터를 적용한다.
      그렇지 않으면 유사도 검색만 수행한다.
    - ``OPENAI_API_KEY``가 있으면 적재와 동일하게 OpenAI 임베딩으로 ``query_embeddings`` 검색한다.
    - 컬렉션이 없거나 비어 있으면 ``[]`` (예외 없음).

    Returns:
        ``[{question, answer, company, position, year, source, distance}, ...]``
    """
    if top_k <= 0:
        raise ValueError("top_k must be greater than 0")

    collection = await asyncio.to_thread(_get_collection_if_nonempty)
    if collection is None:
        return []

    query_text = _build_query_text(question, company_name, position, year)
    where = _build_where_clause(company_name, position, year)

    n = await asyncio.to_thread(collection.count)
    n_results = min(top_k, n)
    if n_results <= 0:
        return []

    if os.getenv("OPENAI_API_KEY"):
        from src.service.github_embedding.openai_embedder import OpenAIEmbedder

        embedder = OpenAIEmbedder()
        vectors = await embedder.embed([query_text])
        return await asyncio.to_thread(
            _query_passed_with_embedding_sync,
            collection,
            vectors[0],
            n_results,
            where,
        )

    return await asyncio.to_thread(
        _query_passed_with_text_sync,
        collection,
        query_text,
        n_results,
        where,
    )
