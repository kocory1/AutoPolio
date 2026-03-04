#!/usr/bin/env python3
"""
레포 코드 인식 전략 비교 실험:
- 전략 A: GitHub Contents API로 전체 파일 트리를 돌면서 코드 파일 내용을 원격에서 바로 읽기
- 전략 B: 레포를 git clone (--depth 1) 한 뒤, 로컬 파일시스템에서 코드 파일을 읽기

측정 지표(대략적인 감):
- 전체 소요 시간 (초)
- HTTP 요청 개수 (Contents API)
- 읽은 파일 개수 / 총 바이트 수

실행 예:
  poetry run python scripts/repo_ingestion_strategy_experiment.py

전제:
- GITHUB_OAUTH_ACCESS_TOKEN 이 설정되어 있어야 한다 (private 레포 실험용).
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

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


@dataclass
class IngestionResult:
    strategy: str
    elapsed_sec: float
    file_count: int
    total_bytes: int
    http_requests: int
    notes: str = ""


def _request(
    method: str,
    url: str,
    *,
    headers: dict,
    params: Optional[dict] = None,
    timeout: int = 20,
) -> Tuple[requests.Response, int]:
    resp = requests.request(method, url, headers=headers, params=params, timeout=timeout)
    return resp, 1


def list_contents_recursive(
    token: str,
    owner: str,
    repo: str,
    path: str = "",
) -> Tuple[List[dict], int]:
    """
    /repos/{owner}/{repo}/contents API를 재귀적으로 돌면서 전체 파일 리스트를 만든다.
    (실제 서비스에서는 Trees API를 고려할 수 있지만, 여기서는 Contents API 전략을 명확히 보기 위해 사용.)
    """
    headers = {"Authorization": f"Bearer {token}"}
    all_items: List[dict] = []
    pending: List[str] = [path]
    total_requests = 0

    while pending:
        current = pending.pop()
        if current:
            url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{current}"
        else:
            url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents"
        resp, used = _request("GET", url, headers=headers)
        total_requests += used
        resp.raise_for_status()
        data = resp.json()
        items = data if isinstance(data, list) else [data]
        for item in items:
            item_path = item.get("path") or item.get("name")
            if not item_path:
                continue
            all_items.append(item)
            if item.get("type") == "dir":
                pending.append(item_path)

    return all_items, total_requests


def fetch_files_via_contents_api(
    token: str,
    owner: str,
    repo: str,
    exts: Tuple[str, ...],
) -> IngestionResult:
    """
    전략 A: Contents API로 전체 파일 목록을 구하고, 지정 확장자 파일을 전부 읽는다.
    """
    print("\n[전략 A] Contents API로 레포 읽기 시작...")
    t0 = time.perf_counter()
    items, list_req = list_contents_recursive(token, owner, repo, "")

    headers_raw = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3.raw",
    }
    http_requests = list_req
    file_count = 0
    total_bytes = 0

    for item in items:
        if item.get("type") != "file":
            continue
        path = item.get("path") or ""
        if not path or not path.endswith(exts):
            continue
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}"
        resp, used = _request("GET", url, headers=headers_raw)
        http_requests += used
        if resp.status_code >= 400:
            continue
        content = resp.content
        file_count += 1
        total_bytes += len(content)

    elapsed = time.perf_counter() - t0
    return IngestionResult(
        strategy="contents_api",
        elapsed_sec=elapsed,
        file_count=file_count,
        total_bytes=total_bytes,
        http_requests=http_requests,
        notes="GitHub Contents API + raw 파일 요청",
    )


def clone_repo_to_temp(
    token: Optional[str],
    owner: str,
    repo: str,
    branch: Optional[str] = None,
) -> Path:
    """
    전략 B에서 사용할 git clone 헬퍼.
    - token 이 있으면 private 레포도 HTTPS로 clone (URL에는 찍히지만 print/log는 하지 않는다).
    """
    tmp_dir = Path(tempfile.mkdtemp(prefix="repo_clone_"))
    if token:
        # token은 로그에 찍히지 않도록 주의한다.
        clone_url = f"https://{token}:x-oauth-basic@github.com/{owner}/{repo}.git"
    else:
        clone_url = f"https://github.com/{owner}/{repo}.git"

    cmd = ["git", "clone", "--depth", "1"]
    if branch:
        cmd += ["--branch", branch]
    cmd += [clone_url, str(tmp_dir)]

    # stdout/stderr를 캡처만 하고 출력은 하지 않는다 (토큰 노출 방지).
    proc = subprocess.run(
        cmd,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return tmp_dir


def iter_files(root: Path, exts: Tuple[str, ...]) -> Iterable[Path]:
    for path in root.rglob("*"):
        if path.is_file() and path.suffix in exts:
            yield path


def fetch_files_via_clone(
    token: Optional[str],
    owner: str,
    repo: str,
    exts: Tuple[str, ...],
    branch: Optional[str] = None,
) -> IngestionResult:
    """
    전략 B: git clone 후, 로컬에서 코드 파일을 전부 읽는다.
    HTTP 요청 수는 git clone 1회로 본다 (대략적인 비교).
    """
    print("\n[전략 B] git clone 후 로컬에서 레포 읽기 시작...")
    t0 = time.perf_counter()
    clone_path = clone_repo_to_temp(token, owner, repo, branch=branch)

    file_count = 0
    total_bytes = 0
    for path in iter_files(clone_path, exts):
        try:
            data = path.read_bytes()
        except Exception:
            continue
        file_count += 1
        total_bytes += len(data)

    elapsed = time.perf_counter() - t0
    # 대략적인 비교를 위해 git clone 전체를 HTTP 1회로 취급
    http_requests = 1
    return IngestionResult(
        strategy="git_clone",
        elapsed_sec=elapsed,
        file_count=file_count,
        total_bytes=total_bytes,
        http_requests=http_requests,
        notes=f"git clone (--depth 1, branch={branch or 'default'}) 후 로컬 파일 읽기",
    )


def choose_repo_interactively(token: str) -> Tuple[str, str]:
    print("대상 레포를 입력하세요.")
    print("  (1) 본인 레포 목록에서 선택")
    print("  (2) owner/repo 직접 입력")
    choice = input("1 또는 2: ").strip()

    if choice == "2":
        raw = input("owner/repo (예: kocory1/AutoPolio): ").strip()
        if "/" not in raw:
            raise RuntimeError("형식: owner/repo")
        owner, repo = raw.split("/", 1)
        return owner, repo

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
        raise RuntimeError("레포가 없습니다.")

    print("\n레포 목록 (최근 15개):")
    for i, r in enumerate(repos[:15], 1):
        print(f"  {i:2}. {r.get('full_name')}  (private={r.get('private')})")
    idx_str = input("번호 입력: ").strip()
    if not idx_str.isdigit():
        raise RuntimeError("숫자를 입력하세요.")
    idx = int(idx_str)
    if not (1 <= idx <= len(repos)):
        raise RuntimeError("범위 밖입니다.")
    r = repos[idx - 1]
    full_name = r.get("full_name", "")
    owner, repo = full_name.split("/", 1)
    return owner, repo


def main() -> None:
    print("=== 레포 코드 인식 전략 비교 실험 (Contents API vs git clone) ===\n")
    token = get_github_token()
    owner, repo = choose_repo_interactively(token)
    print(f"\n대상 레포: {owner}/{repo}")
    branch = input("실험할 브랜치 이름 (엔터=기본 브랜치): ").strip() or None

    # 어떤 확장자를 “코드 파일”로 볼지
    exts = (".py", ".js", ".ts", ".tsx", ".java", ".go", ".rs", ".md")
    print(f"\n타깃 파일 확장자: {exts}")

    # 전략 A: Contents API
    result_a = fetch_files_via_contents_api(token, owner, repo, exts)

    # 전략 B: git clone
    # NOTE: private 레포일 경우 token을 사용해 HTTPS clone을 시도한다.
    result_b = fetch_files_via_clone(token, owner, repo, exts, branch=branch)

    print("\n=== 결과 비교 ===")
    for r in (result_a, result_b):
        print(f"\n[{r.strategy}] {r.notes}")
        print(f"- 소요 시간: {r.elapsed_sec:.2f} 초")
        print(f"- 파일 수: {r.file_count}")
        print(f"- 총 바이트 수: {r.total_bytes}")
        print(f"- HTTP 요청 수(대략): {r.http_requests}")

    print("\n=== 요약 코멘트 가이드 ===")
    print("- Contents API는 요청 수가 많아지고, 레포가 클수록 느릴 수 있지만,")
    print("  클론 없이도 바로 파일 내용을 읽을 수 있어 서버에서 간단히 사용할 수 있다.")
    print("- git clone은 초기 1회 비용이 크지만, 이후에는 로컬에서 빠르게 여러 번 읽고 가공하기 좋다.")
    print("- AutoFolio 요구사항 기준으로, 어떤 전략이 더 적합한지 week2 이슈 문서에 2~3문단으로 정리하면 된다.")


if __name__ == "__main__":
    main()

