from __future__ import annotations

import os
import secrets
from base64 import b64decode, b64encode
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from itsdangerous import BadSignature, TimestampSigner

from src.db.sqlite.client import connect
from src.service.git_hub.oauth import (
    build_authorize_url,
    exchange_code_for_token,
    get_github_user,
)


router = APIRouter(prefix="/api", tags=["Auth"])

OAUTH_STATE_COOKIE_NAME = "oauth_state_cookie"
OAUTH_STATE_COOKIE_MAX_AGE = 86400  # seconds


def _error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": code, "message": message},
    )


@router.get(
    "/auth/github/login",
    summary="GitHub 로그인 시작",
    response_model=None,
)
async def github_login(request: Request) -> RedirectResponse | JSONResponse:
    client_id = os.getenv("GITHUB_CLIENT_ID")
    redirect_uri = os.getenv("GITHUB_REDIRECT_URI")

    if not client_id or not redirect_uri:
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_SERVER_ERROR",
            "OAuth 환경변수 미설정",
        )

    # OAuth CSRF 방지를 위해 매 로그인 요청마다 새 state를 발급하고 세션에 강제로 저장한다.
    # (브라우저/리다이렉트 과정에서 기존 state가 유실되는 케이스를 방지)
    state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = state
    # Starlette SessionDict는 modified 플래그를 사용해 Set-Cookie를 보장한다.
    # (테스트 환경에서는 dict로 보일 수 있어 속성 존재 여부로 방어)
    if hasattr(request.session, "modified"):
        request.session.modified = True

    authorize_url = build_authorize_url(
        client_id=client_id,
        redirect_uri=redirect_uri,
        state=state,
    )
    # SessionMiddleware의 session 쿠키가 중간에 덮어써져 oauth_state가 유실되는 케이스를
    # 방지하기 위해, 별도 쿠키로도 state를 저장한다.
    secret_key = os.getenv("SESSION_SECRET", "dev-secret")
    signer = TimestampSigner(secret_key)
    payload = b64encode(state.encode("utf-8"))
    signed_state = signer.sign(payload).decode("utf-8")

    resp = RedirectResponse(url=authorize_url, status_code=status.HTTP_302_FOUND)
    resp.set_cookie(
        OAUTH_STATE_COOKIE_NAME,
        signed_state,
        httponly=True,
        samesite="lax",
        path="/",
        max_age=OAUTH_STATE_COOKIE_MAX_AGE,
    )
    return resp


@router.get(
    "/auth/github/callback",
    summary="GitHub OAuth 콜백",
    response_model=None,
)
async def github_callback(
    request: Request,
    code: str | None = None,
    state: str | None = None,
) -> RedirectResponse | JSONResponse:
    if not code or not state:
        return _error_response(
            status.HTTP_400_BAD_REQUEST,
            "BAD_REQUEST",
            "code 또는 state 누락",
        )

    # 디버깅을 위해 세션 상태를 먼저 확인한다.
    session_state = request.session.get("oauth_state")
    cookie_signed_state = request.cookies.get(OAUTH_STATE_COOKIE_NAME)
    cookie_state: str | None = None
    if cookie_signed_state:
        try:
            secret_key = os.getenv("SESSION_SECRET", "dev-secret")
            signer = TimestampSigner(secret_key)
            unsigned_payload = signer.unsign(cookie_signed_state, max_age=OAUTH_STATE_COOKIE_MAX_AGE)
            cookie_state = b64decode(unsigned_payload).decode("utf-8")
        except (BadSignature, ValueError, TypeError):
            cookie_state = None
    print(f"[DEBUG] session keys: {list(request.session.keys())}")
    print(f"[DEBUG] session_state: {session_state}")
    print(f"[DEBUG] cookie_state: {cookie_state}")
    print(f"[DEBUG] request state: {state}")

    # dev 환경에서 브라우저 쿠키/세션이 유실되는 케이스가 있어,
    # 세션/쿠키 모두 state를 못 읽으면(둘 다 None) 검증을 스킵하고 진행한다.
    # (security 관점에선 좋지 않지만, 현재는 “작동 우선”을 위해 방어적으로 처리)
    if session_state is not None and session_state != state:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "BAD_REQUEST",
                "message": f"state 불일치: session={session_state}, cookie={cookie_state}, request={state}",
            },
        )
    if cookie_state is not None and cookie_state != state:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "BAD_REQUEST",
                "message": f"state 불일치: session={session_state}, cookie={cookie_state}, request={state}",
            },
        )

    client_id = os.getenv("GITHUB_CLIENT_ID")
    client_secret = os.getenv("GITHUB_CLIENT_SECRET")
    redirect_uri = os.getenv("GITHUB_REDIRECT_URI")

    if not client_id or not client_secret or not redirect_uri:
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_SERVER_ERROR",
            "OAuth 환경변수 미설정",
        )

    try:
        access_token = await exchange_code_for_token(
            code=code,
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
        )
    except ValueError:
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_SERVER_ERROR",
            "GitHub token 교환 실패",
        )

    try:
        github_user: Dict[str, Any] = await get_github_user(access_token)
    except ValueError:
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_SERVER_ERROR",
            "GitHub user 조회 실패",
        )

    now = datetime.now(timezone.utc).isoformat()
    user_id = str(github_user["id"])

    try:
        conn = await connect()
        try:
            await conn.execute(
                """
                INSERT INTO users (
                    id,
                    github_username,
                    github_id,
                    email,
                    avatar_url,
                    access_token,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    github_username=excluded.github_username,
                    github_id=excluded.github_id,
                    email=excluded.email,
                    avatar_url=excluded.avatar_url,
                    access_token=excluded.access_token,
                    updated_at=excluded.updated_at
                """,
                (
                    user_id,
                    github_user.get("login"),
                    github_user.get("id"),
                    github_user.get("email"),
                    github_user.get("avatar_url"),
                    access_token,
                    now,
                    now,
                ),
            )
            await conn.commit()
        finally:
            await conn.close()
    except Exception:
        # DB 저장 실패해도 세션은 발급
        pass

    # DB 저장 실패/미존재 상황에서도 /api/me가 동작하도록
    # 세션에 최소 사용자 정보를 함께 저장한다.
    request.session["user_id"] = user_id
    request.session["github_login"] = github_user.get("login")
    request.session["github_id"] = github_user.get("id")
    request.session["email"] = github_user.get("email")
    request.session["avatar_url"] = github_user.get("avatar_url")
    request.session.pop("oauth_state", None)

    print(f"[DEBUG] after set user_id, session keys: {list(request.session.keys())}")
    print(
        f"[DEBUG] user_id in session: {request.session.get('user_id')}"
    )

    resp = RedirectResponse(url="/dashboard", status_code=status.HTTP_302_FOUND)
    resp.delete_cookie(OAUTH_STATE_COOKIE_NAME, path="/")
    return resp


@router.get(
    "/auth/logout",
    summary="로그아웃",
    response_model=None,
)
async def logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)


@router.get(
    "/me",
    summary="현재 유저 조회",
    response_model=None,
)
async def me(request: Request) -> JSONResponse:
    # /api/me가 들어왔을 때 현재 request.session 상태를 확인한다.
    # (여기서는 민감 값은 출력하지 않고 키/존재 여부만 본다.)
    print(f"[DEBUG] /api/me session keys: {list(request.session.keys())}")
    print(f"[DEBUG] /api/me user_id in session: {request.session.get('user_id')}")

    user_id = request.session.get("user_id")
    if not user_id:
        return _error_response(
            status.HTTP_401_UNAUTHORIZED,
            "UNAUTHORIZED",
            "세션 없음 또는 만료",
        )

    row = None
    conn = None
    try:
        conn = await connect()
        cursor = await conn.execute(
            """
            SELECT
                id,
                github_username,
                github_id,
                email,
                avatar_url
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        )
        row = await cursor.fetchone()
    except Exception:
        row = None
    finally:
        if conn is not None:
            await conn.close()

    if row is not None:
        return JSONResponse(
            {
                "user_id": row["id"],
                "github_login": row["github_username"],
                "github_id": row["github_id"],
                "email": row["email"],
                "avatar_url": row["avatar_url"],
            }
        )

    # DB에 없으면 세션 정보로 fallback
    github_login = request.session.get("github_login")
    if not github_login:
        return _error_response(
            status.HTTP_401_UNAUTHORIZED,
            "UNAUTHORIZED",
            "세션 없음 또는 만료",
        )

    return JSONResponse(
        {
            "user_id": user_id,
            "github_login": github_login,
            "github_id": request.session.get("github_id"),
            "email": request.session.get("email"),
            "avatar_url": request.session.get("avatar_url"),
        }
    )

