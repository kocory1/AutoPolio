"""service.rag.passed_samples — 쿼리/where 빌더 및 빈 컬렉션 동작."""

import pytest

from src.service.rag import retrieve_passed_cover_letters
from src.service.rag.passed_samples import (
    _build_query_text,
    _build_where_clause,
)


def test_build_query_text_full_when_all_meta_present() -> None:
    q = _build_query_text(
        "회고 분석을 서술하세요",
        company_name="콜로소",
        position="데이터 분석가",
        year="2022",
    )
    assert q == (
        "콜로소의 2022년 데이터 분석가 공고의 자기소개서 문항 1 : 회고 분석을 서술하세요"
    )


def test_build_query_text_short_when_company_missing() -> None:
    q = _build_query_text(
        "회고 분석을 서술하세요",
        company_name=None,
        position="데이터 분석가",
        year="2022",
    )
    assert q == "자기소개서 문항 1 : 회고 분석을 서술하세요"


def test_build_query_text_short_when_any_meta_blank() -> None:
    q = _build_query_text(
        "x",
        company_name="  ",
        position="p",
        year="2024",
    )
    assert q == "자기소개서 문항 1 : x"


def test_build_where_none_when_all_missing() -> None:
    assert _build_where_clause(None, None, None) is None


def test_build_where_none_when_only_one_or_two_fields() -> None:
    assert _build_where_clause("ACME", None, None) is None
    assert _build_where_clause("ACME", "백엔드", None) is None
    assert _build_where_clause(None, "백엔드", "2024") is None


def test_build_where_and_three_fields() -> None:
    w = _build_where_clause("ACME", "백엔드", "2024")
    assert w == {
        "$and": [
            {"company": {"$eq": "ACME"}},
            {"position": {"$eq": "백엔드"}},
            {"year": {"$eq": "2024"}},
        ]
    }


@pytest.mark.asyncio
async def test_retrieve_returns_empty_when_collection_missing(monkeypatch) -> None:
    class FakeClient:
        def get_collection(self, name: str):
            raise ValueError("no such collection")

    monkeypatch.setattr(
        "src.service.rag.passed_samples.get_chroma_client",
        lambda: FakeClient(),
    )
    out = await retrieve_passed_cover_letters("문항", top_k=3)
    assert out == []


@pytest.mark.asyncio
async def test_retrieve_raises_on_invalid_top_k() -> None:
    with pytest.raises(ValueError, match="top_k"):
        await retrieve_passed_cover_letters("q", top_k=0)
