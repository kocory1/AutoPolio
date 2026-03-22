from __future__ import annotations

import urllib.parse
from typing import Any, Dict

import httpx


def build_authorize_url(
    client_id: str,
    redirect_uri: str,
    state: str,
    scope: str = "read:user user:email",
) -> str:
    base = "https://github.com/login/oauth/authorize"
    query = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": scope,
        }
    )
    return f"{base}?{query}"


async def exchange_code_for_token(
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> str:
    url = "https://github.com/login/oauth/access_token"
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

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, json=payload, headers=headers, timeout=10)
        except httpx.HTTPError as exc:
            raise ValueError("GitHub token exchange failed") from exc

    data = resp.json()

    if "error" in data or "access_token" not in data:
        raise ValueError("GitHub token exchange failed")

    return str(data["access_token"])


async def get_github_user(access_token: str) -> Dict[str, Any]:
    url = "https://api.github.com/user"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
    }

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise ValueError("Failed to fetch GitHub user") from exc

    data = resp.json()

    # 최소 필드만 추려서 반환
    return {
        "id": int(data["id"]),
        "login": str(data["login"]),
        "email": data.get("email"),
        "avatar_url": str(data["avatar_url"]),
    }

