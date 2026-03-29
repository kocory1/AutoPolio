"""
합격 자소서(문항 단위) ChromaDB 조회.

스키마: docs/AUTOFOLIO_합격자소서_벡터DB_스키마.md
컬렉션: `passed_cover_letters` (없거나 비어 있으면 빈 리스트).
"""

from __future__ import annotations

import asyncio
from typing import Any

from src.db.vector.chroma import get_chroma_client

PASSED_COVER_LETTERS_COLLECTION = "passed_cover_letters"


def _strip_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    s = value.strip()
    return s if s else None


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
    y = _strip_or_none(year)
    if c and p and y:
        return f"{c}의 {y}년 {p} 공고의 자기소개서 문항 1 : {q}"
    return f"자기소개서 문항 1 : {q}"


def _build_where_clause(
    company_name: str | None,
    position: str | None,
    year: str | None,
) -> dict[str, Any] | None:
    """제공된 메타 필드에 대해서만 $eq 조건을 쌓고, 2개 이상이면 $and."""
    conditions: list[dict[str, Any]] = []
    c = _strip_or_none(company_name)
    if c is not None:
        conditions.append({"company": {"$eq": c}})
    p = _strip_or_none(position)
    if p is not None:
        conditions.append({"position": {"$eq": p}})
    y = _strip_or_none(year)
    if y is not None:
        conditions.append({"year": {"$eq": y}})

    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


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


def _retrieve_passed_cover_letters_sync(
    question: str,
    company_name: str | None,
    position: str | None,
    year: str | None,
    top_k: int,
) -> list[dict[str, Any]]:
    client = get_chroma_client()
    try:
        collection = client.get_collection(name=PASSED_COVER_LETTERS_COLLECTION)
    except Exception:
        return []

    try:
        n = collection.count()
    except Exception:
        return []

    if n == 0:
        return []

    query_text = _build_query_text(question, company_name, position, year)
    where = _build_where_clause(company_name, position, year)

    n_results = min(top_k, n)
    if n_results <= 0:
        return []

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


async def retrieve_passed_cover_letters(
    question: str,
    company_name: str | None = None,
    position: str | None = None,
    year: str | None = None,
    top_k: int = 5,
) -> list[dict]:
    """합격 자소서 문항 청크를 유사도 검색한다.

    - 쿼리 텍스트는 스키마 문서와 동일한 포맷(또는 메타 미완 시 축약 포맷)으로 구성한다.
    - ``company`` / ``position`` / ``year`` 메타는 값이 넘겨진 필드에 한해 where 필터로 적용한다.
    - 컬렉션이 없거나 비어 있으면 ``[]`` (예외 없음).

    Returns:
        ``[{question, answer, company, position, year, source, distance}, ...]``
    """
    if top_k <= 0:
        raise ValueError("top_k must be greater than 0")

    return await asyncio.to_thread(
        _retrieve_passed_cover_letters_sync,
        question,
        company_name,
        position,
        year,
        top_k,
    )
