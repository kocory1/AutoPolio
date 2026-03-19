from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

import httpx

GITHUB_API_BASE = "https://api.github.com"

_REPO_ID_DIGITS = re.compile(r"^\d+$")


def _normalize_path(path: str | None) -> str:
    if not path or path == "/":
        return ""
    return path.strip("/")


def _parse_owner_repo(repo_id: str) -> Tuple[str, str]:
    """
    repo_id가 "owner/repo" 형태일 때만 동작.
    숫자 repo_id는 이 함수 밖에서 resolve 한다.
    """
    if "/" not in repo_id:
        raise ValueError(f"Invalid repo_id format: {repo_id}")
    owner, repo = repo_id.split("/", 1)
    if not owner or not repo:
        raise ValueError(f"Invalid repo_id format: {repo_id}")
    return owner, repo


async def resolve_repo_owner_repo(
    access_token: str,
    repo_id: str,
) -> Tuple[int | None, str, str, str]:
    """
    repo_id가
    - 숫자: GitHub /repositories/{id}로 resolve
    - owner/repo: 그대로 파싱
    를 수행한다.

    Returns:
      (github_repo_id, owner, repo, full_name)
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
    }

    if _REPO_ID_DIGITS.match(repo_id):
        repo_num = int(repo_id)
        url = f"{GITHUB_API_BASE}/repositories/{repo_num}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        full_name = str(data["full_name"])
        owner, repo = _parse_owner_repo(full_name)
        return int(data["id"]), owner, repo, full_name

    owner, repo = _parse_owner_repo(repo_id)
    # GitHub repo numeric id는 이 단계에서 알 수 없으므로 None
    return None, owner, repo, f"{owner}/{repo}"


async def list_user_repos(
    access_token: str,
    *,
    page: int = 1,
    per_page: int = 30,
) -> Dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
    }
    params = {"page": page, "per_page": per_page}

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{GITHUB_API_BASE}/user/repos",
            headers=headers,
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()

    repos: list[dict[str, Any]] = []
    for r in data:
        repos.append(
            {
                "id": int(r["id"]),
                "full_name": r["full_name"],
                "description": r.get("description"),
                "private": bool(r.get("private", False)),
                "language": r.get("language"),
                "stargazers_count": int(r.get("stargazers_count", 0)),
                "forks_count": int(r.get("forks_count", 0)),
                "default_branch": r.get("default_branch"),
                "pushed_at": r.get("pushed_at"),
            }
        )

    # GitHub API는 전체 total_count를 바로 주지 않으므로 응답 크기를 사용한다.
    return {"repos": repos, "page": page, "per_page": per_page, "total_count": len(repos)}


async def list_repo_files_tree(
    access_token: str,
    *,
    owner: str,
    repo: str,
    path: str = "",
    # depth=-1이면 GitHub에 있는 트리를 끝까지(단, traverse_cap까지) 순회한다.
    depth: int = -1,
    traverse_cap: int = 500,
    ref: str | None = None,
) -> Dict[str, Any]:
    """
    Contents API를 재귀로 돌려 tree 형태로 반환한다.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
    }

    normalized = _normalize_path(path)
    root = "/" if not normalized else f"{normalized}/"

    tree: list[dict[str, Any]] = []
    visited_nodes = 0
    capped = False

    # remaining<=0이면 더 깊게 내려가지 않는다.
    # depth=-1이면 remaining=None으로 무제한 순회(단, traverse_cap까지)로 처리한다.
    remaining0: int | None = depth if depth >= 0 else None

    async def _walk(
        current_path: str,
        current_depth_remaining: int | None,
    ) -> None:
        nonlocal visited_nodes, capped
        if capped or visited_nodes >= traverse_cap:
            return

        url = (
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents"
            if not current_path
            else f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{current_path}"
        )
        params: dict[str, str] = {}
        if ref:
            params["ref"] = ref

        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, params=params, timeout=10)
            resp.raise_for_status()
            items = resp.json()

        items_list: list[dict[str, Any]] = items if isinstance(items, list) else [items]
        for item in items_list:
            if capped or visited_nodes >= traverse_cap:
                capped = True
                break

            item_type = item.get("type")
            item_path = item.get("path") or item.get("name")
            if not item_type or not item_path:
                continue

            tree.append({"path": str(item_path), "type": str(item_type)})
            visited_nodes += 1

            if item_type == "dir" and (current_depth_remaining is None or current_depth_remaining > 0):
                next_remaining = (
                    None if current_depth_remaining is None else current_depth_remaining - 1
                )
                await _walk(str(item_path), next_remaining)

    await _walk(normalized, remaining0)

    return {
        "repo_id": None,
        "ref": ref,
        "root": root,
        "tree": tree,
        "traverse_cap": traverse_cap,
        "visited_nodes": visited_nodes,
        "capped": capped,
    }


async def get_repo_content(
    access_token: str,
    *,
    owner: str,
    repo: str,
    path: str,
    ref: str | None = None,
    encoding: str = "raw",
) -> Any:
    headers = {
        "Authorization": f"Bearer {access_token}",
    }
    params: dict[str, str] = {}
    if ref:
        params["ref"] = ref

    if encoding == "raw":
        headers["Accept"] = "application/vnd.github.v3.raw"
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, params=params, timeout=10)
            resp.raise_for_status()
            return resp.text

    if encoding == "base64":
        headers["Accept"] = "application/vnd.github+json"
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=headers, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        # GitHub returns content as base64 string already.
        return data

    raise ValueError("Invalid encoding")


async def list_repo_commits(
    access_token: str,
    *,
    owner: str,
    repo: str,
    author: str | None = None,
    path: str | None = None,
    since: str | None = None,
    until: str | None = None,
    page: int = 1,
    per_page: int = 30,
    ref: str | None = None,
) -> Dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
    }

    params: dict[str, Any] = {"page": page, "per_page": per_page}
    if author:
        params["author"] = author
    if path:
        params["path"] = path
    if since:
        params["since"] = since
    if until:
        params["until"] = until
    if ref:
        params["sha"] = ref

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits",
            headers=headers,
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        commits = resp.json()

        detailed: list[dict[str, Any]] = []
        for c in commits:
            sha = c.get("sha")
            if not sha:
                continue
            detail = await client.get(
                f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits/{sha}",
                headers=headers,
                timeout=10,
            )
            detail.raise_for_status()
            detailed.append(detail.json())

    commit_items: list[dict[str, Any]] = []
    dates: list[str] = []
    files_total = 0
    for d in detailed:
        sha = d.get("sha")
        commit = d.get("commit", {}) or {}
        author_info = d.get("author") or {}
        files = d.get("files") or []
        files_total += len(files)

        date = commit.get("author", {}).get("date")
        if date:
            dates.append(date)

        commit_items.append(
            {
                "sha": sha,
                "message": (commit.get("message") or "").splitlines()[0],
                "author": {
                    "login": author_info.get("login"),
                    "name": author_info.get("name"),
                    "email": author_info.get("email"),
                },
                "html_url": d.get("html_url"),
                "files_changed": len(files),
                "date": date,
            }
        )

    date_from = min(dates) if dates else None
    date_to = max(dates) if dates else None

    return {
        "repo_id": None,
        "ref": ref,
        "author": author,
        "summary": {
            "total_commits": len(commit_items),
            "author_commits": len(commit_items) if author else 0,
            "files_changed_total": files_total,
            "date_range": {"from": date_from, "to": date_to},
        },
        "commits": commit_items,
        "page": page,
        "per_page": per_page,
    }

