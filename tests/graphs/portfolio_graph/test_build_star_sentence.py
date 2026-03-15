"""portfolio_graph.build_star_sentence pytest 단위 테스트."""

import pytest

from src.graphs.portfolio_graph.node import build_star_sentence


@pytest.mark.asyncio
async def test_returns_error_when_context_missing():
    result = await build_star_sentence({"profile": {}, "assets": []})

    assert result["error"] == "insufficient_context_for_star"
    assert result["project_candidates"] == []


@pytest.mark.asyncio
async def test_generates_star_candidates_per_repo(monkeypatch):
    async def fake_call_openai_for_star(profile, assets, consistency_feedback):
        assert profile["id"] == "u1"
        assert len(assets) == 1
        assert consistency_feedback == {}
        repo = assets[0]["metadata"]["repo"]
        return [
            {
                "situation": "트래픽 급증",
                "task": "응답 지연 개선",
                "action": f"{repo} 쿼리 튜닝",
                "result": "p95 35% 개선",
            }
        ]

    monkeypatch.setattr(
        "src.graphs.portfolio_graph.node._call_openai_for_star",
        fake_call_openai_for_star,
    )

    result = await build_star_sentence(
        {
            "profile": {"id": "u1"},
            "selected_repos": ["owner/repo-a", "owner/repo-b"],
            "repo_assets_map": {
                "owner/repo-a": [
                    {
                        "id": "asset-a",
                        "document": "repo-a 성능 개선",
                        "metadata": {"repo": "owner/repo-a"},
                    }
                ],
                "owner/repo-b": [
                    {
                        "id": "asset-b",
                        "document": "repo-b 배포 자동화",
                        "metadata": {"repo": "owner/repo-b"},
                    }
                ],
            },
            "consistency_feedback": {},
        }
    )

    assert len(result["project_candidates"]) == 2
    assert result["project_candidates"][0]["repo"] == "owner/repo-a"
    assert result["project_candidates"][1]["repo"] == "owner/repo-b"
    assert result["project_candidates"][0]["star_candidates"][0]["result"] == "p95 35% 개선"


@pytest.mark.asyncio
async def test_returns_error_when_openai_call_fails(monkeypatch):
    async def fake_call_openai_for_star(profile, assets, consistency_feedback):
        raise RuntimeError("openai down")

    monkeypatch.setattr(
        "src.graphs.portfolio_graph.node._call_openai_for_star",
        fake_call_openai_for_star,
    )

    result = await build_star_sentence(
        {
            "profile": {"id": "u1"},
            "selected_repos": ["owner/repo-a"],
            "repo_assets_map": {
                "owner/repo-a": [
                    {
                        "id": "asset-1",
                        "document": "성능 개선",
                        "metadata": {"repo": "owner/repo-a"},
                    }
                ]
            },
        }
    )

    assert result["error"] == "build_star_sentence_failed: RuntimeError"
    assert result["project_candidates"] == []
    assert result["repo_errors"] == {"owner/repo-a": "RuntimeError"}


@pytest.mark.asyncio
async def test_continues_when_some_repos_fail(monkeypatch):
    async def fake_call_openai_for_star(profile, assets, consistency_feedback):
        repo = assets[0]["metadata"]["repo"]
        if repo == "owner/repo-a":
            raise RuntimeError("openai down")
        return [
            {
                "situation": "장애 빈발",
                "task": "배포 안정화",
                "action": "CI 파이프라인 정비",
                "result": "배포 실패율 40% 감소",
            }
        ]

    monkeypatch.setattr(
        "src.graphs.portfolio_graph.node._call_openai_for_star",
        fake_call_openai_for_star,
    )

    result = await build_star_sentence(
        {
            "profile": {"id": "u1"},
            "selected_repos": ["owner/repo-a", "owner/repo-b"],
            "repo_assets_map": {
                "owner/repo-a": [
                    {
                        "id": "asset-a",
                        "document": "repo-a 이슈",
                        "metadata": {"repo": "owner/repo-a"},
                    }
                ],
                "owner/repo-b": [
                    {
                        "id": "asset-b",
                        "document": "repo-b 개선",
                        "metadata": {"repo": "owner/repo-b"},
                    }
                ],
            },
        }
    )

    assert "error" not in result
    assert len(result["project_candidates"]) == 1
    assert result["project_candidates"][0]["repo"] == "owner/repo-b"
    assert result["repo_errors"] == {"owner/repo-a": "RuntimeError"}


@pytest.mark.asyncio
async def test_records_no_assets_in_repo_errors(monkeypatch):
    async def fake_call_openai_for_star(profile, assets, consistency_feedback):
        return [
            {
                "situation": "S",
                "task": "T",
                "action": "A",
                "result": "R",
            }
        ]

    monkeypatch.setattr(
        "src.graphs.portfolio_graph.node._call_openai_for_star",
        fake_call_openai_for_star,
    )

    result = await build_star_sentence(
        {
            "profile": {"id": "u1"},
            "selected_repos": ["owner/repo-a", "owner/repo-b"],
            "repo_assets_map": {
                "owner/repo-a": [],
                "owner/repo-b": [
                    {
                        "id": "asset-b",
                        "document": "repo-b 개선",
                        "metadata": {"repo": "owner/repo-b"},
                    }
                ],
            },
        }
    )

    assert "error" not in result
    assert len(result["project_candidates"]) == 1
    assert result["project_candidates"][0]["repo"] == "owner/repo-b"
    assert result["repo_errors"] == {"owner/repo-a": "no_assets"}


@pytest.mark.asyncio
async def test_returns_insufficient_context_when_all_repos_have_no_assets():
    result = await build_star_sentence(
        {
            "profile": {"id": "u1"},
            "selected_repos": ["owner/repo-a", "owner/repo-b"],
            "repo_assets_map": {
                "owner/repo-a": [],
                "owner/repo-b": [],
            },
        }
    )

    assert result["error"] == "insufficient_context_for_star"
    assert result["project_candidates"] == []
    assert result["repo_errors"] == {
        "owner/repo-a": "no_assets",
        "owner/repo-b": "no_assets",
    }

