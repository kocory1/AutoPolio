"""portfolio_graph.build_portfolio 단위 테스트."""

from src.graphs.portfolio_graph.node import build_portfolio


def test_build_portfolio_returns_projects_for_selected_repos():
    result = build_portfolio(
        {
            "profile": {"id": "u1", "github_username": "mspark"},
            "selected_repos": ["owner/repo-a", "owner/repo-b"],
            "project_candidates": [
                {
                    "repo": "owner/repo-a",
                    "star_candidates": [
                        {
                            "situation": "트래픽 급증",
                            "task": "응답 지연 개선",
                            "action": "쿼리 튜닝",
                            "result": "p95 35% 개선",
                        }
                    ],
                },
                {
                    "repo": "owner/repo-b",
                    "star_candidates": [
                        {
                            "situation": "장애 빈발",
                            "task": "배포 안정화",
                            "action": "CI 파이프라인 정비",
                            "result": "배포 실패율 40% 감소",
                        }
                    ],
                },
            ],
        }
    )

    portfolio = result["portfolio"]
    assert portfolio["title"] == "mspark 포트폴리오"
    assert len(portfolio["projects"]) == 2
    assert portfolio["projects"][0]["repo"] == "owner/repo-a"
    assert portfolio["projects"][0]["stars"][0]["result"] == "p95 35% 개선"
    assert portfolio["projects"][1]["repo"] == "owner/repo-b"


def test_build_portfolio_filters_invalid_star_candidates():
    result = build_portfolio(
        {
            "profile": {"id": "u1"},
            "selected_repos": ["owner/repo-a"],
            "project_candidates": [
                {
                    "repo": "owner/repo-a",
                    "star_candidates": [
                        {
                            "situation": "S",
                            "task": "T",
                            "action": "A",
                            "result": "R",
                        },
                        {
                            "situation": "S2",
                            "task": "T2",
                            "action": "A2",
                        },
                    ],
                }
            ],
        }
    )

    stars = result["portfolio"]["projects"][0]["stars"]
    assert len(stars) == 1
    assert stars[0]["result"] == "R"


def test_build_portfolio_returns_fallback_intro_when_star_missing():
    result = build_portfolio(
        {
            "profile": {"id": "u1"},
            "selected_repos": ["owner/repo-a"],
            "project_candidates": [],
        }
    )

    project = result["portfolio"]["projects"][0]
    assert project["repo"] == "owner/repo-a"
    assert project["stars"] == []
    assert "근거 STAR가 부족" in project["intro"]


def test_build_portfolio_handles_empty_selected_repos():
    result = build_portfolio(
        {
            "profile": {"id": "u1"},
            "selected_repos": [],
            "project_candidates": [],
        }
    )

    portfolio = result["portfolio"]
    assert portfolio["projects"] == []
    assert "0개 레포" in portfolio["summary"]
