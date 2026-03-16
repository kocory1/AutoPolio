"""service.rag.user_assets 단위 테스트."""

import pytest

from src.service.rag import retrieve_user_assets
from src.service.rag.user_assets import PORTFOLIO_STAR_QUERIES, PORTFOLIO_STAR_QUERY


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------

def _make_fake_query_sync(return_value: list[dict] | None = None):
    """_query_user_assets_sync 를 대체하는 fake. captured 딕셔너리에 호출 내역 누적."""
    calls: list[dict] = []

    def fake(user_id, query_text, where, top_k):
        calls.append({"user_id": user_id, "query_text": query_text, "where": where, "top_k": top_k})
        return return_value or []

    fake.calls = calls  # type: ignore[attr-defined]
    return fake


# ---------------------------------------------------------------------------
# 기본 반환 형식
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_retrieve_user_assets_returns_normalized_result(monkeypatch):
    fake = _make_fake_query_sync(
        [
            {
                "id": "owner/repo/src/auth/login.py",
                "document": "JWT 로그인 처리",
                "metadata": {
                    "type": "code",
                    "source": "github",
                    "repo": "owner/repo",
                    "path": "src/auth/login.py",
                },
                "distance": 0.12,
            }
        ]
    )
    monkeypatch.setattr("src.service.rag.user_assets._query_user_assets_sync", fake)

    result = await retrieve_user_assets(user_id="u1", top_k=5)

    assert len(result) == 1
    assert result[0]["id"] == "owner/repo/src/auth/login.py"
    assert result[0]["metadata"]["path"] == "src/auth/login.py"


# ---------------------------------------------------------------------------
# 유효성 검사
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_retrieve_user_assets_raises_when_user_id_missing():
    with pytest.raises(ValueError, match="user_id is required"):
        await retrieve_user_assets(user_id="")


@pytest.mark.asyncio
async def test_retrieve_user_assets_raises_when_top_k_invalid():
    with pytest.raises(ValueError, match="top_k must be greater than 0"):
        await retrieve_user_assets(user_id="u1", top_k=0)


# ---------------------------------------------------------------------------
# 다중 쿼리 동작 검증
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_retrieve_user_assets_calls_all_star_queries(monkeypatch):
    """PORTFOLIO_STAR_QUERIES 의 모든 쿼리가 각각 호출되는지 확인한다."""
    fake = _make_fake_query_sync([])
    monkeypatch.setattr("src.service.rag.user_assets._query_user_assets_sync", fake)

    await retrieve_user_assets(user_id="u1", top_k=5)

    called_queries = [c["query_text"] for c in fake.calls]
    assert called_queries == PORTFOLIO_STAR_QUERIES


@pytest.mark.asyncio
async def test_retrieve_user_assets_deduplicates_by_id(monkeypatch):
    """동일 id 문서가 여러 쿼리에서 반환돼도 중복 없이 한 번만 포함된다."""
    dup_doc = {"id": "repo/a.py", "document": "중복 문서", "metadata": {}, "distance": 0.1}

    fake = _make_fake_query_sync([dup_doc])
    monkeypatch.setattr("src.service.rag.user_assets._query_user_assets_sync", fake)

    result = await retrieve_user_assets(user_id="u1", top_k=10)

    ids = [r["id"] for r in result]
    assert ids.count("repo/a.py") == 1


@pytest.mark.asyncio
async def test_retrieve_user_assets_keeps_best_distance_on_duplicate(monkeypatch):
    """동일 id 중복 시 distance 가 가장 낮은 항목을 채택한다."""
    calls_count = 0

    def fake(user_id, query_text, where, top_k):
        nonlocal calls_count
        dist = 0.1 + calls_count * 0.1
        calls_count += 1
        return [{"id": "repo/a.py", "document": "doc", "metadata": {}, "distance": dist}]

    monkeypatch.setattr("src.service.rag.user_assets._query_user_assets_sync", fake)

    result = await retrieve_user_assets(user_id="u1", top_k=10)

    assert len(result) == 1
    assert result[0]["distance"] == pytest.approx(0.1)


@pytest.mark.asyncio
async def test_retrieve_user_assets_treats_zero_distance_as_best(monkeypatch):
    """distance=0.0 이 truthy 처리 버그로 누락되지 않도록 보장한다."""
    calls_count = 0

    def fake(user_id, query_text, where, top_k):
        nonlocal calls_count
        dist = 0.0 if calls_count == 0 else 0.2
        calls_count += 1
        return [{"id": "repo/a.py", "document": "doc", "metadata": {}, "distance": dist}]

    monkeypatch.setattr("src.service.rag.user_assets._query_user_assets_sync", fake)

    result = await retrieve_user_assets(user_id="u1", top_k=10)

    assert len(result) == 1
    assert result[0]["distance"] == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_retrieve_user_assets_respects_top_k_after_merge(monkeypatch):
    """병합 후 최종 반환 수가 top_k 를 초과하지 않는다."""
    docs = [
        {"id": f"repo/file{i}.py", "document": f"doc{i}", "metadata": {}, "distance": float(i)}
        for i in range(10)
    ]

    fake = _make_fake_query_sync(docs)
    monkeypatch.setattr("src.service.rag.user_assets._query_user_assets_sync", fake)

    result = await retrieve_user_assets(user_id="u1", top_k=3)

    assert len(result) <= 3


# ---------------------------------------------------------------------------
# where 절 / 하위 호환
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_retrieve_user_assets_builds_where_clause(monkeypatch):
    fake = _make_fake_query_sync([])
    monkeypatch.setattr("src.service.rag.user_assets._query_user_assets_sync", fake)

    await retrieve_user_assets(
        user_id="u1",
        source_filter=["github", "resume"],
        type_filter=["folder", "project"],
        top_k=3,
    )

    for call in fake.calls:
        assert call["where"] == {
            "$and": [
                {"source": {"$in": ["github", "resume"]}},
                {"type": {"$in": ["folder", "project"]}},
            ]
        }


def test_portfolio_star_query_backward_compat():
    """PORTFOLIO_STAR_QUERY 상수가 삭제되지 않고 유지되는지 확인한다."""
    assert isinstance(PORTFOLIO_STAR_QUERY, str)
    assert len(PORTFOLIO_STAR_QUERY) > 0


def test_portfolio_star_queries_count():
    """PORTFOLIO_STAR_QUERIES 가 5개 쿼리를 포함하는지 확인한다."""
    assert len(PORTFOLIO_STAR_QUERIES) == 5
