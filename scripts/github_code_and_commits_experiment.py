#!/usr/bin/env python3
"""
로컬 실습: README 말고 실제 코드 파일을 읽을 수 있는지,
본인 레포가 아닌 타인 레포에서도 내가 커밋한 것만 조회되는지 검증한다.

필요 환경변수:
- GITHUB_OAUTH_ACCESS_TOKEN (또는 실행 시 입력)

실행 예:
  poetry run python scripts/github_code_and_commits_experiment.py
"""

import os
from typing import Any, Optional

import requests

GITHUB_API_BASE = "https://api.github.com"


def get_github_token() -> str:
    env_token = os.environ.get("GITHUB_OAUTH_ACCESS_TOKEN")
    if env_token:
        return env_token.strip()
    print("GitHub OAuth access token이 필요합니다.")
    token = input("GitHub access token 입력: ").strip()
    if not token:
        raise RuntimeError("GitHub access token이 비어 있습니다.")
    return token


def fetch_user(access_token: str) -> dict:
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(f"{GITHUB_API_BASE}/user", headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()


def list_repo_contents(access_token: str, owner: str, repo: str, path: str = "") -> list[dict]:
    """레포 루트(또는 path) 안의 파일/디렉터리 목록을 조회한다."""
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}" if path else f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents"
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else [data]


def fetch_file_content_raw(access_token: str, owner: str, repo: str, path: str) -> str:
    """특정 파일의 원문(텍스트)을 가져온다. 코드 파일용."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github.v3.raw",
    }
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}"
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.text


def fetch_commits(
    access_token: str,
    owner: str,
    repo: str,
    author: Optional[str] = None,
    per_page: int = 10,
) -> list[dict]:
    """레포 커밋 목록. author를 넣으면 해당 유저 커밋만 (타인 레포에서 내 커밋만 뽑기)."""
    headers = {"Authorization": f"Bearer {access_token}"}
    params: dict[str, Any] = {"per_page": per_page}
    if author:
        params["author"] = author
    url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits"
    resp = requests.get(url, headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def find_one_file_by_ext(
    access_token: str, owner: str, repo: str, path: str, extensions: tuple[str, ...]
) -> Optional[str]:
    """지정한 path(디렉터리) 아래에서 해당 확장자 파일 하나의 경로를 반환. 1단계 하위까지 검사."""
    items = list_repo_contents(access_token, owner, repo, path)
    for item in items:
        if item.get("type") == "file":
            name = item.get("name", "")
            if any(name.endswith(ext) for ext in extensions):
                return item.get("path", name)
        if item.get("type") == "dir":
            sub_path = item.get("path", "")
            sub_items = list_repo_contents(access_token, owner, repo, sub_path)
            for sub in sub_items:
                if sub.get("type") == "file":
                    name = sub.get("name", "")
                    if any(name.endswith(ext) for ext in extensions):
                        return sub.get("path", f"{sub_path}/{name}")
    return None


def main() -> None:
    print("=== 실습: 코드 파일 읽기 + 타인 레포에서 내 커밋만 조회 ===\n")
    token = get_github_token()
    user = fetch_user(token)
    login = user.get("login")
    print(f"로그인: {login} (id={user.get('id')})\n")

    # 레포 선택: 본인 레포 목록에서 고르거나 owner/repo 직접 입력
    print("대상 레포를 입력하세요.")
    print("  (1) 본인 레포 목록에서 선택")
    print("  (2) owner/repo 직접 입력 (타인 레포 가능)")
    choice = input("1 또는 2: ").strip()

    if choice == "2":
        raw = input("owner/repo (예: kocory1/AutoPolio): ").strip()
        if "/" not in raw:
            print("형식: owner/repo")
            return
        owner, repo = raw.split("/", 1)
        full_name = f"{owner}/{repo}"
    else:
        # 본인 레포 목록
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(
            f"{GITHUB_API_BASE}/user/repos",
            headers=headers,
            params={"per_page": 30, "sort": "pushed"},
            timeout=10,
        )
        resp.raise_for_status()
        repos = resp.json()
        if not repos:
            print("레포가 없습니다.")
            return
        print("\n레포 목록 (최근 15개):")
        for i, r in enumerate(repos[:15], 1):
            print(f"  {i:2}. {r.get('full_name')}  (private={r.get('private')})")
        idx_str = input("번호 입력: ").strip()
        if not idx_str.isdigit():
            print("숫자를 입력하세요.")
            return
        idx = int(idx_str)
        if not (1 <= idx <= len(repos)):
            print("범위 밖입니다.")
            return
        r = repos[idx - 1]
        full_name = r.get("full_name", "")
        owner, repo = full_name.split("/", 1)

    print(f"\n대상 레포: {full_name}\n")

    # ----- 실험 1: 레포 안 파일·폴더 목록 + README/코드 둘 다 읽기 -----
    print("--- 실험 1: 파일/폴더 목록 + README·코드 파일 접근 ---")
    try:
        root_items = list_repo_contents(token, owner, repo, "")
        print("  [루트 목록]")
        for x in root_items:
            t = x.get("type", "?")
            name = x.get("name", "?")
            print(f"    {t:4}  {name}")
    except Exception as e:
        print("  루트 목록 조회 오류:", e)
        root_items = []

    # README 또는 아무 .md 파일 하나 읽기
    md_path = find_one_file_by_ext(token, owner, repo, "", (".md",))
    if md_path:
        print(f"\n  [문서 파일 읽기] {md_path}")
        try:
            content = fetch_file_content_raw(token, owner, repo, md_path)
            lines = content.splitlines()
            for line in lines[:12]:
                print("   ", line[:90])
            if len(lines) > 12:
                print("   ...")
            print("  -> 문서(README 등) 읽기 OK.")
        except Exception as e:
            print("  오류:", e)
    else:
        print("  .md 파일 없음 (스킵)")

    # 코드 파일(.py, .js 등) 하나 읽기
    code_path = find_one_file_by_ext(token, owner, repo, "", (".py", ".js", ".ts", ".java", ".go", ".rs"))
    if code_path:
        print(f"\n  [코드 파일 읽기] {code_path}")
        try:
            content = fetch_file_content_raw(token, owner, repo, code_path)
            lines = content.splitlines()
            for line in lines[:20]:
                print("   ", line[:90])
            if len(lines) > 20:
                print("   ...")
            print("  -> 코드 파일 읽기 OK.")
        except Exception as e:
            print("  오류:", e)
    else:
        print("  코드 확장자(.py 등) 파일 없음 (스킵)")

    print("  -> 레포 안 파일·폴더 목록과, 문서/코드 내용 접근 모두 가능.")

    # ----- 실험 2: 타인 레포에서 author=내 로그인 으로 내 커밋만 조회 -----
    print("\n--- 실험 2: 이 레포에서 '내 커밋만' 조회 (author={}) ---".format(login))
    try:
        commits = fetch_commits(token, owner, repo, author=login, per_page=10)
        if not commits:
            print("  이 레포에서 본인(author={}) 커밋이 없거나 조회되지 않았습니다.".format(login))
            print("  (본인 레포가 아니어도, 본인이 기여한 커밋은 author 파라미터로 필터 가능합니다.)")
        else:
            print(f"  조회된 커밋 수: {len(commits)}")
            for c in commits[:5]:
                info = c.get("commit", {})
                msg = (info.get("message") or "").splitlines()[0][:60]
                author_info = info.get("author", {})
                name = author_info.get("name", "?")
                date = author_info.get("date", "?")[:10]
                sha = c.get("sha", "")[:7]
                print(f"    - {sha}  {date}  {name}  {msg}")
            print("  -> 타인 레포에서도 author=본인로그인 으로 내 커밋만 가져오기 가능.")
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            print("  레포를 찾을 수 없거나 접근 권한이 없습니다 (404).")
        else:
            print("  HTTP 오류:", e)
    except Exception as e:
        print("  오류:", e)

    print("\n--- 실험 종료 ---")


if __name__ == "__main__":
    main()
