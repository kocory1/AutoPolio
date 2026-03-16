"""
User Asset 조회 서비스.

문서 스키마(`type`, `source`, `repo`, `path`) 기준으로
ChromaDB `user_assets_{user_id}` 컬렉션을 조회한다.
"""

from __future__ import annotations

import asyncio
from typing import Any

from src.db.vector import get_user_asset_collection

# ---------------------------------------------------------------------------
# Retrieval 쿼리 — GitHub 임베딩 문서(커밋·PR·README·코드)와
# STAR 서술 언어 사이의 의미 거리를 좁히기 위해
# STAR 관점별로 쿼리를 분리해 recall 을 높인다.
# ---------------------------------------------------------------------------

# 하위 호환용 단일 쿼리 (외부에서 직접 참조하는 경우 대비)
PORTFOLIO_STAR_QUERY = (
    "developer portfolio STAR evidence impact troubleshooting architecture collaboration"
)

# 다중 쿼리: STAR 관점별 5개 쿼리
PORTFOLIO_STAR_QUERIES: list[str] = [
    # Situation / Task — 문제 상황·목표 발굴
    (
        "문제 상황 발견 배경 기술 부채 레거시 병목 장애 요구사항 "
        "problem context legacy bottleneck incident requirement background"
    ),
    # Action — 트러블슈팅·성능 개선
    (
        "버그 수정 디버깅 트러블슈팅 성능 최적화 응답 속도 개선 메모리 CPU 쿼리 튜닝 "
        "bug fix debugging troubleshooting performance optimization latency throughput query tuning"
    ),
    # Action — 설계·아키텍처·리팩토링
    (
        "시스템 설계 아키텍처 리팩토링 모듈화 분리 추상화 패턴 의존성 역전 "
        "system design architecture refactoring modularization abstraction design pattern dependency"
    ),
    # Action — 기능 구현·개발 기여
    (
        "기능 구현 개발 API 서비스 컴포넌트 통합 배포 자동화 CI CD 테스트 코드 작성 "
        "feature implementation API service component integration deployment automation CI CD test coverage"
    ),
    # Result — 측정 가능한 성과·임팩트
    (
        "성과 임팩트 개선율 감소 단축 증가 사용자 경험 팀 생산성 비즈니스 효과 "
        "result impact improvement reduction increase user experience team productivity business value metric"
    ),
]


def _build_where_clause(
    source_filter: list[str] | None,
    type_filter: list[str] | None,
) -> dict[str, Any] | None:
    """Chroma where 절을 생성한다."""
    conditions: list[dict[str, Any]] = []
    if source_filter:
        conditions.append({"source": {"$in": source_filter}})
    if type_filter:
        conditions.append({"type": {"$in": type_filter}})

    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


def _normalize_results(raw: dict[str, Any]) -> list[dict]:
    """Chroma query 결과를 표준 dict 리스트로 변환한다."""
    ids = (raw.get("ids") or [[]])[0]
    docs = (raw.get("documents") or [[]])[0]
    metas = (raw.get("metadatas") or [[]])[0]
    dists = (raw.get("distances") or [[]])[0]

    results: list[dict] = []
    for idx, item_id in enumerate(ids):
        results.append(
            {
                "id": item_id,
                "document": docs[idx] if idx < len(docs) else None,
                "metadata": metas[idx] if idx < len(metas) else None,
                "distance": dists[idx] if idx < len(dists) else None,
            }
        )
    return results


def _query_user_assets_sync(
    user_id: str,
    query_text: str,
    where: dict[str, Any] | None,
    top_k: int,
) -> list[dict]:
    collection = get_user_asset_collection(user_id)
    kwargs: dict[str, Any] = {
        "query_texts": [query_text],
        "n_results": top_k,
    }
    if where is not None:
        kwargs["where"] = where
    raw = collection.query(**kwargs)
    return _normalize_results(raw)


def _merge_and_deduplicate(results_per_query: list[list[dict]], top_k: int) -> list[dict]:
    """다중 쿼리 결과를 id 기준으로 중복 제거 후 distance 오름차순으로 반환한다.

    동일 문서가 여러 쿼리에서 검색된 경우 가장 낮은(가까운) distance를 채택한다.
    """
    def _distance_value(item: dict) -> float:
        value = item.get("distance")
        return float("inf") if value is None else float(value)

    seen: dict[str, dict] = {}
    for results in results_per_query:
        for item in results:
            item_id = item["id"]
            if item_id not in seen:
                seen[item_id] = item
            else:
                existing_dist = _distance_value(seen[item_id])
                new_dist = _distance_value(item)
                if new_dist < existing_dist:
                    seen[item_id] = item

    merged = sorted(seen.values(), key=_distance_value)
    return merged[:top_k]


async def retrieve_user_assets(
    user_id: str,
    source_filter: list[str] | None = None,
    type_filter: list[str] | None = None,
    top_k: int = 20,
) -> list[dict]:
    """유저 에셋을 조회해 반환한다.

    - STAR 관점별 다중 쿼리로 GitHub 임베딩 문서와의 의미 거리를 좁혀 recall 향상
    - 각 쿼리마다 top_k 개씩 검색 후 id 기준 중복 제거, distance 오름차순으로 최종 top_k 반환
    - source/type 필터는 where 절로 적용
    - 반환: [{id, document, metadata, distance}, ...]
    """
    if not user_id:
        raise ValueError("user_id is required")
    if top_k <= 0:
        raise ValueError("top_k must be greater than 0")

    where = _build_where_clause(source_filter, type_filter)

    results_per_query = await asyncio.gather(
        *[
            asyncio.to_thread(_query_user_assets_sync, user_id, query, where, top_k)
            for query in PORTFOLIO_STAR_QUERIES
        ]
    )

    return _merge_and_deduplicate(list(results_per_query), top_k)
