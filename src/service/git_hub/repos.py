from __future__ import annotations

import re
from typing import Any, Dict, Tuple
from urllib.parse import quote

import httpx

GITHUB_API_BASE = "https://api.github.com"


class GitHubTreeTruncatedError(Exception):
    """GitHub GET /git/trees?recursive=1 응답에서 truncated=true 인 경우."""

    def __init__(self, message: str = "GitHub tree response truncated (too large)") -> None:
        super().__init__(message)

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


def _looks_like_git_commit_sha(ref: str) -> bool:
    s = ref.strip().lower()
    if len(s) < 7 or len(s) > 40:
        return False
    return all(c in "0123456789abcdef" for c in s)


async def _get_default_branch(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    owner: str,
    repo: str,
) -> str:
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
    resp = await client.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    b = data.get("default_branch")
    if not b:
        raise ValueError("default_branch missing from repo")
    return str(b)


async def _get_commit_sha_from_branch(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    owner: str,
    repo: str,
    branch: str,
) -> str:
    enc = quote(branch, safe="")
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/git/ref/heads/{enc}"
    resp = await client.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    obj = data.get("object") or {}
    sha = obj.get("sha")
    if not sha:
        raise ValueError("git ref heads: object.sha missing")
    return str(sha)


async def _get_tree_sha_from_commit(
    client: httpx.AsyncClient,
    headers: dict[str, str],
    owner: str,
    repo: str,
    commit_sha: str,
) -> str:
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/git/commits/{commit_sha}"
    resp = await client.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    tree = data.get("tree") or {}
    tsha = tree.get("sha")
    if not tsha:
        raise ValueError("git commit: tree.sha missing")
    return str(tsha)


async def list_repo_files_tree(
    access_token: str,
    *,
    owner: str,
    repo: str,
    path: str = "",
    # depth=-1이면 경로 깊이 필터 없음.
    depth: int = -1,
    ref: str | None = None,
) -> Dict[str, Any]:
    """
    Git Trees API(recursive=1)로 레포 전체 트리를 한 번에 가져와 반환한다.

    - GET /repos/{owner}/{repo}/git/ref/heads/{branch} 로 커밋 SHA 조회 (또는 ref가 커밋 SHA면 직접 사용)
    - GET /repos/{owner}/{repo}/git/commits/{sha} 로 tree SHA 조회
    - GET /repos/{owner}/{repo}/git/trees/{tree_sha}?recursive=1
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json",
    }

    normalized = _normalize_path(path)
    root = "/" if not normalized else f"{normalized}/"

    async with httpx.AsyncClient() as client:
        if ref is None:
            branch_name = await _get_default_branch(client, headers, owner, repo)
            commit_sha = await _get_commit_sha_from_branch(
                client, headers, owner, repo, branch_name
            )
            resolved_ref = branch_name
        elif _looks_like_git_commit_sha(ref):
            commit_sha = ref.strip().lower()
            resolved_ref = commit_sha
        else:
            commit_sha = await _get_commit_sha_from_branch(
                client, headers, owner, repo, ref
            )
            resolved_ref = ref

        tree_sha = await _get_tree_sha_from_commit(
            client, headers, owner, repo, commit_sha
        )

        tree_url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/git/trees/{tree_sha}"
        resp = await client.get(
            tree_url,
            headers=headers,
            params={"recursive": "1"},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()

    if data.get("truncated") is True:
        raise GitHubTreeTruncatedError()

    raw_tree: list[dict[str, Any]] = data.get("tree") or []
    entries: list[dict[str, str]] = []

    for item in raw_tree:
        t = item.get("type")
        p = item.get("path")
        if not p or not isinstance(p, str):
            continue
        if t == "blob":
            entries.append({"path": p, "type": "file"})
        elif t == "tree":
            dir_path = p if p.endswith("/") else f"{p}/"
            entries.append({"path": dir_path, "type": "dir"})
        else:
            continue

    def _path_for_match(e: dict[str, str]) -> str:
        return e["path"].rstrip("/") if e["type"] == "dir" else e["path"]

    prefix_norm = normalized  # already no leading/trailing slashes

    def _under_prefix(entry_path: str) -> bool:
        if not prefix_norm:
            return True
        if entry_path == prefix_norm:
            return True
        return entry_path.startswith(prefix_norm + "/")

    def _relative_to_prefix(entry_path: str) -> str | None:
        if not prefix_norm:
            return entry_path
        if entry_path == prefix_norm:
            return ""
        if entry_path.startswith(prefix_norm + "/"):
            return entry_path[len(prefix_norm) + 1 :]
        return None

    filtered_entries: list[dict[str, str]] = []
    for e in entries:
        ep = _path_for_match(e)
        if not _under_prefix(ep):
            continue
        if depth < 0:
            filtered_entries.append(e)
            continue
        rel = _relative_to_prefix(ep)
        if rel is None:
            continue
        if rel.count("/") > depth:
            continue
        filtered_entries.append(e)

    entries = filtered_entries

    entries.sort(key=lambda x: x["path"])

    return {
        "repo_id": None,
        "ref": resolved_ref,
        "root": root,
        "tree": entries,
        "visited_nodes": len(entries),
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

