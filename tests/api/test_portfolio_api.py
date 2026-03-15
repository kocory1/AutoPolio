"""포트폴리오 API 테스트."""

import aiosqlite
from fastapi.testclient import TestClient

from src.app.main import app

client = TestClient(app)


def test_generate_requires_auth_header():
    response = client.post("/api/portfolio/generate", json={})

    assert response.status_code == 401
    assert response.json() == {
        "error": "UNAUTHORIZED",
        "message": "UNAUTHORIZED",
    }


def test_generate_returns_error_when_selected_repos_missing(monkeypatch):
    class FakeGraph:
        async def ainvoke(self, state):
            return {"error": "no_selected_repos"}

    monkeypatch.setattr("src.api.portfolio.build_portfolio_graph", lambda: FakeGraph())

    response = client.post(
        "/api/portfolio/generate",
        headers={"X-User-Id": "u1"},
        json={},
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": "BAD_REQUEST",
        "message": "NO_SELECTED_REPOS",
    }


def test_generate_saves_and_returns_portfolio(monkeypatch):
    class FakeGraph:
        async def ainvoke(self, state):
            return {
                "portfolio": {
                    "title": "u1 포트폴리오",
                    "summary": "요약",
                    "projects": [{"repo": "owner/repo-a", "intro": "소개", "stars": []}],
                }
            }

    async def fake_create_portfolio(user_id: str, content: dict):
        return {
            "portfolio_id": "p1",
            "user_id": user_id,
            "created_at": "2026-03-06T00:00:00+00:00",
            "updated_at": "2026-03-06T00:00:00+00:00",
        }

    monkeypatch.setattr("src.api.portfolio.build_portfolio_graph", lambda: FakeGraph())
    monkeypatch.setattr("src.api.portfolio.create_portfolio", fake_create_portfolio)

    response = client.post(
        "/api/portfolio/generate",
        headers={"X-User-Id": "u1"},
        json={},
    )

    assert response.status_code == 200
    assert response.json()["portfolio_id"] == "p1"
    assert response.json()["portfolio"]["projects"][0]["repo"] == "owner/repo-a"


def test_generate_maps_user_not_found_error(monkeypatch):
    class FakeGraph:
        async def ainvoke(self, state):
            return {"error": "user_not_found"}

    monkeypatch.setattr("src.api.portfolio.build_portfolio_graph", lambda: FakeGraph())

    response = client.post(
        "/api/portfolio/generate",
        headers={"X-User-Id": "u1"},
        json={},
    )

    assert response.status_code == 404
    assert response.json() == {
        "error": "NOT_FOUND",
        "message": "USER_NOT_FOUND",
    }


def test_generate_maps_load_profile_failed_error(monkeypatch):
    class FakeGraph:
        async def ainvoke(self, state):
            return {"error": "load_profile_failed: RuntimeError"}

    monkeypatch.setattr("src.api.portfolio.build_portfolio_graph", lambda: FakeGraph())

    response = client.post(
        "/api/portfolio/generate",
        headers={"X-User-Id": "u1"},
        json={},
    )

    assert response.status_code == 500
    assert response.json() == {
        "error": "INTERNAL_SERVER_ERROR",
        "message": "LOAD_PROFILE_FAILED",
    }


def test_generate_maps_unclassified_graph_error(monkeypatch):
    class FakeGraph:
        async def ainvoke(self, state):
            return {"error": "insufficient_context_for_star"}

    monkeypatch.setattr("src.api.portfolio.build_portfolio_graph", lambda: FakeGraph())

    response = client.post(
        "/api/portfolio/generate",
        headers={"X-User-Id": "u1"},
        json={},
    )

    assert response.status_code == 500
    assert response.json() == {
        "error": "INTERNAL_SERVER_ERROR",
        "message": "PORTFOLIO_GRAPH_FAILED",
    }


def test_generate_returns_error_when_portfolio_persist_fails(monkeypatch):
    class FakeGraph:
        async def ainvoke(self, state):
            return {
                "portfolio": {
                    "title": "u1 포트폴리오",
                    "summary": "요약",
                    "projects": [],
                }
            }

    async def fake_create_portfolio(user_id: str, content: dict):
        raise aiosqlite.IntegrityError("duplicate key")

    monkeypatch.setattr("src.api.portfolio.build_portfolio_graph", lambda: FakeGraph())
    monkeypatch.setattr("src.api.portfolio.create_portfolio", fake_create_portfolio)

    response = client.post(
        "/api/portfolio/generate",
        headers={"X-User-Id": "u1"},
        json={},
    )

    assert response.status_code == 500
    assert response.json() == {
        "error": "INTERNAL_SERVER_ERROR",
        "message": "PORTFOLIO_PERSIST_FAILED",
    }


def test_get_list_requires_auth_header():
    response = client.get("/api/portfolio")

    assert response.status_code == 401
    assert response.json() == {
        "error": "UNAUTHORIZED",
        "message": "UNAUTHORIZED",
    }


def test_get_portfolio_list(monkeypatch):
    async def fake_list_portfolios(user_id: str):
        return [{"portfolio_id": "p1", "created_at": "2026-03-06T00:00:00+00:00", "updated_at": "2026-03-06T00:00:00+00:00"}]

    monkeypatch.setattr("src.api.portfolio.list_portfolios", fake_list_portfolios)

    response = client.get("/api/portfolio", headers={"X-User-Id": "u1"})

    assert response.status_code == 200
    assert response.json()["items"][0]["portfolio_id"] == "p1"


def test_get_portfolio_by_id_not_found(monkeypatch):
    async def fake_get_portfolio_by_id(user_id: str, portfolio_id: str):
        return None

    monkeypatch.setattr("src.api.portfolio.get_portfolio_by_id", fake_get_portfolio_by_id)

    response = client.get(
        "/api/portfolio",
        headers={"X-User-Id": "u1"},
        params={"portfolio_id": "missing"},
    )

    assert response.status_code == 404
    assert response.json() == {
        "error": "NOT_FOUND",
        "message": "PORTFOLIO_NOT_FOUND",
    }

