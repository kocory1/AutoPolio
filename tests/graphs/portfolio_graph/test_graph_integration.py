"""portfolio_graph 그래프 통합 플로우 테스트."""

import pytest

from src.graphs.portfolio_graph import graph as graph_module


@pytest.mark.asyncio
async def test_graph_ends_after_load_profile_error(monkeypatch):
    calls: list[str] = []

    async def fake_load_profile(state):
        calls.append("load_profile")
        return {
            "error": "user_not_found",
            "profile": {},
            "assets": [],
            "selected_repos": [],
            "repo_assets_map": {},
        }

    async def fake_build_star_sentence(state):
        calls.append("build_star_sentence")
        return {"project_candidates": []}

    async def fake_self_consistency(state):
        calls.append("self_consistency")
        return {"is_hallucination": False, "is_star": True}

    def fake_build_portfolio(state):
        calls.append("build_portfolio")
        return {"portfolio": {"projects": []}}

    monkeypatch.setattr(graph_module, "load_profile", fake_load_profile)
    monkeypatch.setattr(graph_module, "build_star_sentence", fake_build_star_sentence)
    monkeypatch.setattr(graph_module, "self_consistency", fake_self_consistency)
    monkeypatch.setattr(graph_module, "build_portfolio", fake_build_portfolio)

    graph = graph_module.build_portfolio_graph()
    result = await graph.ainvoke({"user_id": "u1"})

    assert result["error"] == "user_not_found"
    assert calls == ["load_profile"]


@pytest.mark.asyncio
async def test_graph_happy_path(monkeypatch):
    calls: list[str] = []

    async def fake_load_profile(state):
        calls.append("load_profile")
        return {
            "profile": {"id": "u1"},
            "assets": [{"id": "asset-1", "document": "성능 개선"}],
            "selected_repos": ["owner/repo-a"],
            "repo_assets_map": {
                "owner/repo-a": [{"id": "asset-1", "document": "성능 개선"}]
            },
        }

    async def fake_build_star_sentence(state):
        calls.append("build_star_sentence")
        return {
            "project_candidates": [
                {
                    "repo": "owner/repo-a",
                    "star_candidates": [
                        {"situation": "S", "task": "T", "action": "A", "result": "R"}
                    ],
                }
            ]
        }

    async def fake_self_consistency(state):
        calls.append("self_consistency")
        return {
            "is_hallucination": False,
            "is_star": True,
            "star_retry_count": state.get("star_retry_count", 0),
            "consistency_feedback": {},
        }

    def fake_build_portfolio(state):
        calls.append("build_portfolio")
        return {
            "portfolio": {
                "projects": [
                    {
                        "repo": "owner/repo-a",
                        "intro": "프로젝트 소개",
                        "stars": [{"situation": "S", "task": "T", "action": "A", "result": "R"}],
                    }
                ]
            }
        }

    monkeypatch.setattr(graph_module, "load_profile", fake_load_profile)
    monkeypatch.setattr(graph_module, "build_star_sentence", fake_build_star_sentence)
    monkeypatch.setattr(graph_module, "self_consistency", fake_self_consistency)
    monkeypatch.setattr(graph_module, "build_portfolio", fake_build_portfolio)

    graph = graph_module.build_portfolio_graph()
    result = await graph.ainvoke({"user_id": "u1"})

    assert result["portfolio"]["projects"][0]["repo"] == "owner/repo-a"
    assert calls == [
        "load_profile",
        "build_star_sentence",
        "self_consistency",
        "build_portfolio",
    ]


@pytest.mark.asyncio
async def test_graph_retries_then_passes(monkeypatch):
    calls: list[str] = []
    consistency_call_count = {"n": 0}

    async def fake_load_profile(state):
        calls.append("load_profile")
        return {
            "profile": {"id": "u1"},
            "assets": [{"id": "asset-1"}],
            "selected_repos": ["owner/repo-a"],
            "repo_assets_map": {"owner/repo-a": [{"id": "asset-1"}]},
        }

    async def fake_build_star_sentence(state):
        calls.append("build_star_sentence")
        return {
            "project_candidates": [
                {
                    "repo": "owner/repo-a",
                    "star_candidates": [
                        {"situation": "S", "task": "T", "action": "A", "result": "R"}
                    ],
                }
            ]
        }

    async def fake_self_consistency(state):
        calls.append("self_consistency")
        consistency_call_count["n"] += 1
        if consistency_call_count["n"] == 1:
            return {
                "is_hallucination": True,
                "is_star": False,
                "star_retry_count": 1,
                "consistency_feedback": {"star_fidelity": [{"reason": "보완 필요"}]},
            }
        return {
            "is_hallucination": False,
            "is_star": True,
            "star_retry_count": state.get("star_retry_count", 1),
            "consistency_feedback": {},
        }

    def fake_build_portfolio(state):
        calls.append("build_portfolio")
        return {"portfolio": {"projects": [{"repo": "owner/repo-a"}]}}

    monkeypatch.setattr(graph_module, "load_profile", fake_load_profile)
    monkeypatch.setattr(graph_module, "build_star_sentence", fake_build_star_sentence)
    monkeypatch.setattr(graph_module, "self_consistency", fake_self_consistency)
    monkeypatch.setattr(graph_module, "build_portfolio", fake_build_portfolio)

    graph = graph_module.build_portfolio_graph()
    result = await graph.ainvoke({"user_id": "u1"})

    assert result["portfolio"]["projects"][0]["repo"] == "owner/repo-a"
    assert calls.count("build_star_sentence") == 2
    assert calls.count("self_consistency") == 2
    assert calls[-1] == "build_portfolio"


@pytest.mark.asyncio
async def test_graph_routes_to_portfolio_when_retry_exhausted(monkeypatch):
    calls: list[str] = []
    consistency_call_count = {"n": 0}

    async def fake_load_profile(state):
        calls.append("load_profile")
        return {
            "profile": {"id": "u1"},
            "assets": [{"id": "asset-1"}],
            "selected_repos": ["owner/repo-a"],
            "repo_assets_map": {"owner/repo-a": [{"id": "asset-1"}]},
        }

    async def fake_build_star_sentence(state):
        calls.append("build_star_sentence")
        return {
            "project_candidates": [
                {
                    "repo": "owner/repo-a",
                    "star_candidates": [
                        {"situation": "S", "task": "T", "action": "A", "result": "R"}
                    ],
                }
            ]
        }

    async def fake_self_consistency(state):
        calls.append("self_consistency")
        consistency_call_count["n"] += 1
        return {
            "is_hallucination": True,
            "is_star": False,
            "star_retry_count": consistency_call_count["n"],
            "consistency_feedback": {"hallucination": [{"reason": "근거 부족"}]},
        }

    def fake_build_portfolio(state):
        calls.append("build_portfolio")
        return {"portfolio": {"projects": [{"repo": "owner/repo-a", "stars": []}]}}

    monkeypatch.setattr(graph_module, "load_profile", fake_load_profile)
    monkeypatch.setattr(graph_module, "build_star_sentence", fake_build_star_sentence)
    monkeypatch.setattr(graph_module, "self_consistency", fake_self_consistency)
    monkeypatch.setattr(graph_module, "build_portfolio", fake_build_portfolio)

    graph = graph_module.build_portfolio_graph()
    result = await graph.ainvoke({"user_id": "u1"})

    assert result["portfolio"]["projects"][0]["repo"] == "owner/repo-a"
    assert calls.count("build_star_sentence") == 3
    assert calls.count("self_consistency") == 3
    assert calls[-1] == "build_portfolio"

