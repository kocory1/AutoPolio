#!/usr/bin/env python3
"""
GitHub 레포 하나를 선택해서 메타데이터/README를 읽어오고,
LLM(OpenAI)를 사용해 레포 설명을 만들어보는 실습 스크립트.

필요 환경변수:
- OPENAI_API_KEY: OpenAI API 키

실행 예:
  poetry run python scripts/github_repo_describe_practice.py
"""

import json
import os
from typing import List, Optional

import requests


GITHUB_API_BASE = "https://api.github.com"


def get_github_token() -> str:
    """
    GitHub OAuth access token을 입력받는다.
    (이 토큰은 github_oauth_local_test.py에서 발급 받은 gho_... 토큰)
    """
    env_token = os.environ.get("GITHUB_OAUTH_ACCESS_TOKEN")
    if env_token:
        return env_token.strip()

    print("GitHub OAuth access token이 필요합니다.")
    print("예: gho_xxxxxxxxx  (github_oauth_local_test.py 실행 시 출력된 값)")
    token = input("GitHub access token 입력: ").strip()
    if not token:
        raise RuntimeError("GitHub access token이 비어 있습니다.")
    return token


def fetch_github_user(access_token: str) -> dict:
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(f"{GITHUB_API_BASE}/user", headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()


def fetch_github_repos(access_token: str, per_page: int = 20) -> List[dict]:
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"per_page": per_page, "sort": "pushed"}
    resp = requests.get(f"{GITHUB_API_BASE}/user/repos", headers=headers, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()


def fetch_repo_detail(access_token: str, full_name: str) -> dict:
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(f"{GITHUB_API_BASE}/repos/{full_name}", headers=headers, timeout=10)
    resp.raise_for_status()
    return resp.json()


def fetch_repo_readme(access_token: str, full_name: str) -> Optional[str]:
    """
    README 내용을 텍스트로 가져온다. 없으면 None.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        # raw 형태로 바로 본문을 받기 위한 Accept 헤더
        "Accept": "application/vnd.github.v3.raw",
    }
    resp = requests.get(f"{GITHUB_API_BASE}/repos/{full_name}/readme", headers=headers, timeout=10)
    if resp.status_code == 404:
        return None
    resp.raise_for_status()
    return resp.text


def describe_repo_with_llm(full_name: str, repo_info: dict, readme: Optional[str]) -> str:
    """
    OpenAI LLM을 사용해 레포 설명을 생성한다.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY 환경변수를 설정하세요.")

    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("openai 패키지가 필요합니다. (poetry add openai)")

    client = OpenAI(api_key=api_key)

    meta_summary = {
        "full_name": repo_info.get("full_name"),
        "description": repo_info.get("description"),
        "language": repo_info.get("language"),
        "stargazers_count": repo_info.get("stargazers_count"),
        "forks_count": repo_info.get("forks_count"),
        "open_issues_count": repo_info.get("open_issues_count"),
    }

    readme_text = (readme or "").strip()
    if len(readme_text) > 6000:
        readme_text = readme_text[:6000]

    system_prompt = (
        "당신은 개발자의 GitHub 레포를 분석해 이력서/자기소개서에 쓸 수 있는 설명을 도와주는 도우미입니다. "
        "레포의 목적, 주요 기능, 사용 기술스택을 정리해 주세요."
    )
    user_prompt = f"""다음은 GitHub 레포 한 개에 대한 정보입니다.
1) 레포 메타데이터:
{json.dumps(meta_summary, ensure_ascii=False, indent=2)}

2) README 내용 (일부일 수 있음):
---
{readme_text or "(README 없음)"}
---

위 정보를 바탕으로, 한국어로 다음을 출력하세요:
- 이 레포가 어떤 목적/문제를 다루는 프로젝트인지 (1~2문장)
- 핵심 기능과 특징 (불릿 2~4개)
- 사용된 주요 기술스택 (언어, 프레임워크, 라이브러리 위주로 1문단)

지원자가 자기소개서에서 프로젝트를 설명할 때 바로 가져다 쓸 수 있을 정도로 구체적으로 써 주세요.
"""

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=800,
        temperature=0.3,
    )
    content = (resp.choices[0].message.content or "").strip()
    return content


def main() -> None:
    print("=== GitHub 레포 설명 실습 ===")
    token = get_github_token()

    user = fetch_github_user(token)
    login = user.get("login")
    print(f"\n로그인한 GitHub 사용자: {login} (id={user.get('id')})")

    print("\n최근 레포 최대 20개를 불러옵니다...")
    repos = fetch_github_repos(token, per_page=20)
    if not repos:
        print("레포가 없습니다.")
        return

    print("\n선택 가능한 레포 목록:")
    for idx, repo in enumerate(repos, start=1):
        name = repo.get("full_name")
        desc = repo.get("description") or ""
        print(f"{idx:2d}. {name}  -  {desc[:60]}")

    while True:
        choice_str = input("\n설명을 생성할 레포 번호를 선택하세요 (1~{n}, 취소는 q): ".format(n=len(repos))).strip()
        if choice_str.lower() in {"q", "quit", "exit"}:
            print("취소했습니다.")
            return
        if not choice_str.isdigit():
            print("숫자를 입력하세요.")
            continue
        choice = int(choice_str)
        if not (1 <= choice <= len(repos)):
            print("범위를 벗어난 번호입니다.")
            continue
        break

    target_repo = repos[choice - 1]
    full_name = target_repo.get("full_name")
    print(f"\n선택한 레포: {full_name}")

    print("레포 상세 및 README를 가져오는 중...")
    detail = fetch_repo_detail(token, full_name)
    readme = fetch_repo_readme(token, full_name)

    print("\n== 레포 메타데이터 요약 ==")
    meta_summary = {
        "full_name": detail.get("full_name"),
        "description": detail.get("description"),
        "language": detail.get("language"),
        "stargazers_count": detail.get("stargazers_count"),
        "forks_count": detail.get("forks_count"),
        "open_issues_count": detail.get("open_issues_count"),
    }
    print(json.dumps(meta_summary, ensure_ascii=False, indent=2))

    if readme:
        print("\n(README 내용 일부 미리보기)")
        preview = readme.strip().splitlines()[:15]
        for line in preview:
            print(line)
    else:
        print("\n이 레포에는 README가 없거나 가져올 수 없습니다.")

    print("\n== LLM 기반 레포 설명 ==")
    try:
        description = describe_repo_with_llm(full_name, detail, readme)
    except Exception as e:
        print("LLM 호출 중 오류 발생:", e)
        return

    print("\n--- 레포 설명 ---\n")
    print(description)
    print("\n-----------------\n")


if __name__ == "__main__":
    main()

