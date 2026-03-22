from __future__ import annotations

import json
import os
from base64 import b64encode
from typing import Any, Dict
from unittest.mock import patch

import pytest
from itsdangerous import TimestampSigner
from starlette.testclient import TestClient

from src.app.main import app


@pytest.fixture
def mock_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_CLIENT_ID", "test_client_id")
    monkeypatch.setenv("GITHUB_CLIENT_SECRET", "test_client_secret")
    monkeypatch.setenv(
        "GITHUB_REDIRECT_URI", "http://localhost/api/auth/github/callback"
    )


@pytest.fixture
def client() -> TestClient:
    # FastAPI TestClient (Starlette 기반) 사용
    return TestClient(app)


def _set_session(client: TestClient, data: Dict[str, Any]) -> None:
    """
    Starlette SessionMiddleware가 사용하는 쿠키 포맷에 맞게
    세션 쿠키를 직접 생성한다.
    """
    # `src/app/main.py`에서 SessionMiddleware가 최초 생성될 때의 secret_key와 동일해야 한다.
    # (앱은 테스트 import 시점에 이미 만들어지므로, 여기서 secret_key는 현재 env 기준으로 가져와 서명한다.)
    secret_key = os.getenv("SESSION_SECRET", "dev-secret")
    # Starlette SessionMiddleware와 동일한 방식으로 쿠키 payload를 생성한다:
    #   payload = b64encode(json.dumps(session).encode("utf-8"))
    #   signed = TimestampSigner(secret_key).sign(payload)
    payload = b64encode(json.dumps(data).encode("utf-8"))
    signer = TimestampSigner(secret_key)
    signed = signer.sign(payload).decode("utf-8")
    # SessionMiddleware는 기본 path="/"에서 쿠키를 읽으므로 명시한다.
    client.cookies.set("session", signed, path="/")


# [GET /api/auth/github/login]
def test_login_returns_302(client: TestClient, mock_env: None) -> None:
    response = client.get("/api/auth/github/login", follow_redirects=False)
    assert response.status_code == 302


def test_login_location_contains_github(client: TestClient, mock_env: None) -> None:
    response = client.get("/api/auth/github/login", follow_redirects=False)
    assert "github.com/login/oauth/authorize" in response.headers["location"]


# [GET /api/auth/github/callback]
def test_callback_success(client: TestClient, mock_env: None) -> None:
    # 세션에 oauth_state="test_state" 미리 저장
    _set_session(client, {"oauth_state": "test_state"})

    with patch(
        "src.api.auth.exchange_code_for_token",
        return_value="test_access_token",
    ) as mock_exchange, patch(
        "src.api.auth.get_github_user",
        return_value={
            "id": 12345,
            "login": "testuser",
            "email": "test@example.com",
            "avatar_url": "https://avatars.githubusercontent.com/u/12345",
        },
    ) as mock_get_user:
        response = client.get(
            "/api/auth/github/callback",
            params={"code": "test_code", "state": "test_state"},
            follow_redirects=False,
        )

    assert response.status_code == 302
    assert response.headers["location"] == "/dashboard"
    # GitHub 외부 호출이 시도되었는지 검증 (향후 구현 시)
    mock_exchange.assert_called_once()
    mock_get_user.assert_called_once()


def test_callback_invalid_state(client: TestClient) -> None:
    # 세션에 oauth_state="correct_state" 저장
    _set_session(client, {"oauth_state": "correct_state"})

    response = client.get(
        "/api/auth/github/callback",
        params={"code": "test_code", "state": "wrong_state"},
        follow_redirects=False,
    )
    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "BAD_REQUEST"


def test_callback_missing_code(client: TestClient) -> None:
    response = client.get(
        "/api/auth/github/callback",
        params={"state": "test_state"},
        follow_redirects=False,
    )
    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "BAD_REQUEST"


# [GET /api/auth/logout]
def test_logout_always_302(client: TestClient) -> None:
    response = client.get("/api/auth/logout", follow_redirects=False)
    assert response.status_code == 302


def test_logout_redirects_to_root(client: TestClient) -> None:
    response = client.get("/api/auth/logout", follow_redirects=False)
    assert response.headers["location"] == "/"


# [GET /api/me]
def test_me_authenticated(client: TestClient, mock_env: None) -> None:
    # 세션에 user_id + 유저 정보 저장
    _set_session(
        client,
        {
            "user_id": "test-user-id",
            "github_login": "testuser",
            "github_id": 12345,
            "email": "test@example.com",
            "avatar_url": "https://avatars.githubusercontent.com/u/12345",
        },
    )

    response = client.get("/api/me")
    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == "test-user-id"
    assert body["github_login"] == "testuser"
    assert body["github_id"] == 12345
    assert body["email"] == "test@example.com"
    assert body["avatar_url"] == "https://avatars.githubusercontent.com/u/12345"


def test_me_unauthorized(client: TestClient) -> None:
    response = client.get("/api/me")
    assert response.status_code == 401
    body = response.json()
    assert body["error"] == "UNAUTHORIZED"

