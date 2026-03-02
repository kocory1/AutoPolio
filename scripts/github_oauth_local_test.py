import json
import os
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import requests


GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API_BASE = "https://api.github.com"


class OAuthState:
    def __init__(self, expected_state: str, redirect_uri: str) -> None:
        self.expected_state = expected_state
        self.redirect_uri = redirect_uri
        self.code: str | None = None
        self.error: str | None = None
        self._event = threading.Event()

    def set_code(self, code: str) -> None:
        self.code = code
        self._event.set()

    def set_error(self, message: str) -> None:
        self.error = message
        self._event.set()

    def wait_for_result(self, timeout: float | None = 300.0) -> None:
        self._event.wait(timeout=timeout)


def build_authorize_url(client_id: str, redirect_uri: str, state: str, scope: str) -> str:
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": scope,
        "state": state,
    }
    query = "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items())
    return f"{GITHUB_AUTHORIZE_URL}?{query}"


def start_local_server(host: str, port: int, oauth_state: OAuthState) -> HTTPServer:
    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # type: ignore[override]
            parsed = urlparse(self.path)
            if parsed.path != urlparse(oauth_state.redirect_uri).path:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Not Found")
                return

            query = parse_qs(parsed.query)
            code = query.get("code", [None])[0]
            state = query.get("state", [None])[0]

            if state != oauth_state.expected_state:
                oauth_state.set_error("Invalid state parameter")
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Invalid state parameter")
                return

            if not code:
                oauth_state.set_error("Missing code parameter")
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"Missing code parameter")
                return

            oauth_state.set_code(code)

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            html = "<html><body><h1>GitHub OAuth 성공</h1><p>터미널로 돌아가세요.</p></body></html>"
            self.wfile.write(html.encode("utf-8"))

        def log_message(self, format: str, *args) -> None:  # type: ignore[override]
            # Quiet server logs
            return

    server = HTTPServer((host, port), CallbackHandler)
    return server


def exchange_code_for_token(
    client_id: str, client_secret: str, code: str, redirect_uri: str
) -> dict:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
    }
    response = requests.post(GITHUB_ACCESS_TOKEN_URL, headers=headers, json=payload, timeout=10)
    response.raise_for_status()
    return response.json()


def fetch_github_user(access_token: str) -> dict:
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(f"{GITHUB_API_BASE}/user", headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()


def fetch_github_repos(access_token: str) -> list[dict]:
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(f"{GITHUB_API_BASE}/user/repos", headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()


def main() -> None:
    client_id = os.getenv("GITHUB_OAUTH_CLIENT_ID")
    client_secret = os.getenv("GITHUB_OAUTH_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise RuntimeError(
            "GITHUB_OAUTH_CLIENT_ID / GITHUB_OAUTH_CLIENT_SECRET 환경 변수가 필요합니다."
        )

    host = "localhost"
    port = 8000
    redirect_uri = f"http://{host}:{port}/callback"
    scope = "read:user repo"
    state = secrets.token_urlsafe(32)
    oauth_state = OAuthState(expected_state=state, redirect_uri=redirect_uri)

    authorize_url = build_authorize_url(
        client_id=client_id,
        redirect_uri=redirect_uri,
        state=state,
        scope=scope,
    )

    print("=== GitHub OAuth 로컬 테스트 ===")
    print(f"Redirect URI: {redirect_uri}")
    print("GitHub OAuth App 설정에서 동일한 Callback URL을 등록했는지 확인하세요.\n")
    print("아래 URL로 브라우저에서 접속해 GitHub 로그인을 진행하세요:")
    print(authorize_url)

    try:
        webbrowser.open(authorize_url)
    except Exception:
        # 브라우저 자동 오픈이 실패해도 계속 진행
        pass

    server = start_local_server(host=host, port=port, oauth_state=oauth_state)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    print("\n로컬 서버 대기 중... (Ctrl+C로 중단 가능)")
    oauth_state.wait_for_result()
    server.shutdown()

    if oauth_state.error:
        raise RuntimeError(f"OAuth 실패: {oauth_state.error}")

    if not oauth_state.code:
        raise RuntimeError("콜백에서 code를 받지 못했습니다.")

    print("\n[Step 2] access_token 교환 중...")
    token_response = exchange_code_for_token(
        client_id=client_id,
        client_secret=client_secret,
        code=oauth_state.code,
        redirect_uri=redirect_uri,
    )

    access_token = token_response.get("access_token")
    if not access_token:
        print("토큰 응답:", json.dumps(token_response, ensure_ascii=False, indent=2))
        raise RuntimeError("access_token을 받지 못했습니다.")
    print("access_token:", access_token)# 민감정보 전체 출력 방지

    print("\n[Step 3] GitHub API 호출 테스트...")
    user = fetch_github_user(access_token)
    repos = fetch_github_repos(access_token)

    print("\n== GitHub 유저 정보 ==")
    print(json.dumps({"login": user.get("login"), "id": user.get("id")}, ensure_ascii=False, indent=2))

    print("\n== 레포지토리 샘플 (최대 5개 이름) ==")
    for repo in repos[:5]:
        print("-", repo.get("full_name"))


if __name__ == "__main__":
    main()

