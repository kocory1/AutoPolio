"""portfolio_graph.load_profile pytest 단위 테스트."""

import pytest

from src.graphs.portfolio_graph.node import load_profile


@pytest.mark.asyncio
async def test_returns_error_when_user_id_missing():
    result = await load_profile({})

    assert result["error"] == "user_id is required"
    assert result["profile"] == {}
    assert result["assets"] == []
    assert result["selected_repos"] == []
    assert result["repo_assets_map"] == {}


@pytest.mark.asyncio
async def test_returns_profile_and_assets_from_services(monkeypatch):
    async def fake_get_user_profile(user_id: str):
        assert user_id == "u1"
        return {"id": "u1", "github_username": "mspark"}

    async def fake_retrieve_user_assets(
        user_id: str,
        source_filter: list[str],
        type_filter: list[str],
        top_k: int,
    ):
        assert user_id == "u1"
        assert source_filter == ["github"]
        assert type_filter == ["project", "folder", "code", "document"]
        assert top_k == 20
        return [
            {
                "id": "asset-1",
                "metadata": {"repo": "owner/repo-a"},
                "document": "repo-a 성능 개선",
            },
            {
                "id": "asset-2",
                "metadata": {"repo": "owner/repo-b"},
                "document": "repo-b 배포 자동화",
            },
            {
                "id": "asset-3",
                "metadata": {"repo": "owner/other"},
                "document": "다른 레포",
            },
        ]

    async def fake_get_selected_repos(user_id: str):
        assert user_id == "u1"
        return ["owner/repo-a", "owner/repo-b"]

    monkeypatch.setattr(
        "src.graphs.portfolio_graph.node.get_user_profile",
        fake_get_user_profile,
    )
    monkeypatch.setattr(
        "src.graphs.portfolio_graph.node.retrieve_user_assets",
        fake_retrieve_user_assets,
    )
    monkeypatch.setattr(
        "src.graphs.portfolio_graph.node.get_selected_repos",
        fake_get_selected_repos,
    )

    result = await load_profile({"user_id": "u1"})

    assert result["profile"] == {"id": "u1", "github_username": "mspark"}
    assert result["selected_repos"] == ["owner/repo-a", "owner/repo-b"]
    assert len(result["assets"]) == 2
    assert set(result["repo_assets_map"].keys()) == {"owner/repo-a", "owner/repo-b"}
    assert len(result["repo_assets_map"]["owner/repo-a"]) == 1
    assert len(result["repo_assets_map"]["owner/repo-b"]) == 1
    assert "error" not in result


@pytest.mark.asyncio
async def test_returns_user_not_found_error_when_profile_missing(monkeypatch):
    async def fake_get_user_profile(user_id: str):
        return None

    monkeypatch.setattr(
        "src.graphs.portfolio_graph.node.get_user_profile",
        fake_get_user_profile,
    )

    result = await load_profile({"user_id": "u1"})

    assert result["error"] == "user_not_found"
    assert result["profile"] == {}
    assert result["assets"] == []
    assert result["selected_repos"] == []
    assert result["repo_assets_map"] == {}


@pytest.mark.asyncio
async def test_returns_error_when_selected_repos_missing(monkeypatch):
    async def fake_get_user_profile(user_id: str):
        return {"id": "u1", "github_username": "mspark"}

    async def fake_get_selected_repos(user_id: str):
        return []

    monkeypatch.setattr(
        "src.graphs.portfolio_graph.node.get_user_profile",
        fake_get_user_profile,
    )
    monkeypatch.setattr(
        "src.graphs.portfolio_graph.node.get_selected_repos",
        fake_get_selected_repos,
    )

    result = await load_profile({"user_id": "u1"})

    assert result["error"] == "no_selected_repos"
    assert result["profile"]["id"] == "u1"
    assert result["assets"] == []
    assert result["selected_repos"] == []
    assert result["repo_assets_map"] == {}

