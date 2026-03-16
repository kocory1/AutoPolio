"""portfolio_graph.self_consistency pytest 단위 테스트."""

import pytest

from src.graphs.portfolio_graph.node import self_consistency


@pytest.mark.asyncio
async def test_fails_and_retries_when_star_missing():
    result = await self_consistency({"project_candidates": [], "star_retry_count": 1})

    assert result["is_hallucination"] is False
    assert result["is_star"] is False
    assert result["star_retry_count"] == 2
    assert "hallucination" in result["consistency_feedback"]


@pytest.mark.asyncio
async def test_passes_when_consistency_success(monkeypatch):
    async def fake_call_openai_for_consistency(profile, assets, star):
        assert profile["id"] == "u1"
        assert len(assets) == 1
        assert len(star) == 1
        return {
            "is_hallucination": False,
            "is_star": True,
            "consistency_feedback": {"hallucination": [], "star_fidelity": []},
        }

    monkeypatch.setattr(
        "src.graphs.portfolio_graph.node._call_openai_for_consistency",
        fake_call_openai_for_consistency,
    )

    result = await self_consistency(
        {
            "profile": {"id": "u1"},
            "assets": [{"id": "asset-1", "document": "성능 개선"}],
            "project_candidates": [
                {
                    "repo": "owner/repo-a",
                    "star_candidates": [
                        {"situation": "S", "task": "T", "action": "A", "result": "R"}
                    ],
                }
            ],
            "star_retry_count": 0,
        }
    )

    assert result["is_hallucination"] is False
    assert result["is_star"] is True
    assert result["star_retry_count"] == 0
    assert result["consistency_feedback"] == {}


@pytest.mark.asyncio
async def test_retries_when_consistency_failed(monkeypatch):
    async def fake_call_openai_for_consistency(profile, assets, star):
        return {
            "is_hallucination": True,
            "is_star": True,
            "consistency_feedback": {
                "hallucination": [{"reason": "근거 없는 수치"}],
                "star_fidelity": [],
            },
        }

    monkeypatch.setattr(
        "src.graphs.portfolio_graph.node._call_openai_for_consistency",
        fake_call_openai_for_consistency,
    )

    result = await self_consistency(
        {
            "profile": {"id": "u1"},
            "assets": [{"id": "asset-1"}],
            "project_candidates": [
                {
                    "repo": "owner/repo-a",
                    "star_candidates": [
                        {"situation": "S", "task": "T", "action": "A", "result": "R"}
                    ],
                }
            ],
            "star_retry_count": 2,
        }
    )

    assert result["is_hallucination"] is True
    assert result["is_star"] is True
    assert result["star_retry_count"] == 3
    assert result["consistency_feedback"]["hallucination"][0]["reason"] == "근거 없는 수치"


@pytest.mark.asyncio
async def test_retries_when_consistency_validator_errors(monkeypatch):
    async def fake_call_openai_for_consistency(profile, assets, star):
        raise RuntimeError("openai down")

    monkeypatch.setattr(
        "src.graphs.portfolio_graph.node._call_openai_for_consistency",
        fake_call_openai_for_consistency,
    )

    result = await self_consistency(
        {
            "profile": {"id": "u1"},
            "assets": [{"id": "asset-1"}],
            "project_candidates": [
                {
                    "repo": "owner/repo-a",
                    "star_candidates": [
                        {"situation": "S", "task": "T", "action": "A", "result": "R"}
                    ],
                }
            ],
            "star_retry_count": 0,
        }
    )

    assert result["is_hallucination"] is False
    assert result["is_star"] is False
    assert result["star_retry_count"] == 1
    assert "consistency_validation_unavailable" in result["consistency_feedback"]["hallucination"][0]["reason"]

@pytest.mark.asyncio
async def test_uses_project_candidates(monkeypatch):
    async def fake_call_openai_for_consistency(profile, assets, star):
        assert len(star) == 2
        return {
            "is_hallucination": False,
            "is_star": True,
            "consistency_feedback": {"hallucination": [], "star_fidelity": []},
        }

    monkeypatch.setattr(
        "src.graphs.portfolio_graph.node._call_openai_for_consistency",
        fake_call_openai_for_consistency,
    )

    result = await self_consistency(
        {
            "profile": {"id": "u1"},
            "assets": [{"id": "asset-1"}],
            "project_candidates": [
                {
                    "repo": "owner/repo-a",
                    "star_candidates": [{"situation": "S1", "task": "T1", "action": "A1", "result": "R1"}],
                },
                {
                    "repo": "owner/repo-b",
                    "star_candidates": [{"situation": "S2", "task": "T2", "action": "A2", "result": "R2"}],
                },
            ],
        }
    )

    assert result["is_hallucination"] is False
    assert result["is_star"] is True
