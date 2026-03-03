from __future__ import annotations

"""
GitHub OAuth 로그인 및 GitHub API 호출 유틸리티.

Week1에서 만든 로컬 테스트 스크립트(`github_oauth_local_test.py`)를
실제 서비스 백엔드에서 재사용 가능한 형태로 옮기기 위한 모듈.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import requests


GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API_BASE = "https://api.github.com"


@dataclass
class GitHubOAuthConfig:
    client_id: str
    client_secret: str
    redirect_uri: str
    scope: str = "read:user repo"


def build_authorize_url(config: GitHubOAuthConfig, state: str) -> str:
    params = {
        "client_id": config.client_id,
        "redirect_uri": config.redirect_uri,
        "scope": config.scope,
        "state": state,
    }
    query = "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items())
    return f"{GITHUB_AUTHORIZE_URL}?{query}"


def exchange_code_for_token(
    config: GitHubOAuthConfig,
    code: str,
) -> Dict[str, Any]:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    payload = {
        "client_id": config.client_id,
        "client_secret": config.client_secret,
        "code": code,
        "redirect_uri": config.redirect_uri,
    }
    response = requests.post(GITHUB_ACCESS_TOKEN_URL, headers=headers, json=payload, timeout=10)
    response.raise_for_status()
    return response.json()


def fetch_user(access_token: str) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(f"{GITHUB_API_BASE}/user", headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()


def fetch_repos(access_token: str, per_page: int = 50) -> List[Dict[str, Any]]:
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"per_page": per_page, "sort": "pushed"}
    response = requests.get(f"{GITHUB_API_BASE}/user/repos", headers=headers, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def fetch_commits(
    access_token: str,
    owner: str,
    repo: str,
    author: Optional[str] = None,
    path: Optional[str] = None,
    per_page: int = 50,
) -> List[Dict[str, Any]]:
    headers = {"Authorization": f"Bearer {access_token}"}
    params: Dict[str, Any] = {"per_page": per_page}
    if author:
        params["author"] = author
    if path:
        params["path"] = path
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits"
    response = requests.get(url, headers=headers, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def fetch_tree(
    access_token: str,
    owner: str,
    repo: str,
    path: str = "",
) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {access_token}"}
    api_path = path or ""
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{api_path}"
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()

