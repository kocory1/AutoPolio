"""1번 그래프(포트폴리오 생성) 노드. 내부 로직은 주석으로만 표시."""

import json
import os
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.service.rag import retrieve_user_assets
from src.service.user import get_selected_repos, get_user_profile

from .prompts import CONSISTENCY_SYSTEM_PROMPT, STAR_SYSTEM_PROMPT
from .state import PortfolioState

DEFAULT_STAR_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def _build_chat_openai(temperature: float) -> ChatOpenAI:
    """공통 ChatOpenAI 클라이언트를 생성한다."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    return ChatOpenAI(
        model=DEFAULT_STAR_MODEL,
        temperature=temperature,
        api_key=api_key,
        model_kwargs={"response_format": {"type": "json_object"}},
    )


async def load_profile(state: PortfolioState) -> dict:
    """User 프로필·에셋 로드 (P1 API 또는 DB).

    입력: state["user_id"]
    출력: profile, assets
    """
    user_id = state.get("user_id")
    if not user_id:
        return {
            "error": "user_id is required",
            "profile": {},
            "assets": [],
            "selected_repos": [],
            "repo_assets_map": {},
        }

    try:
        profile = await get_user_profile(user_id)
        if profile is None:
            return {
                "error": "user_not_found",
                "profile": {},
                "assets": [],
                "selected_repos": [],
                "repo_assets_map": {},
            }
        selected_repos = await get_selected_repos(user_id)
        if not selected_repos:
            return {
                "error": "no_selected_repos",
                "profile": profile,
                "assets": [],
                "selected_repos": [],
                "repo_assets_map": {},
            }
        assets = await retrieve_user_assets(
            user_id=user_id,
            source_filter=["github"],
            type_filter=["project", "folder", "code", "document"],
            top_k=20,
        )
    except Exception as exc:  # pragma: no cover - defensive path
        return {
            "error": f"load_profile_failed: {type(exc).__name__}",
            "profile": {},
            "assets": [],
            "selected_repos": [],
            "repo_assets_map": {},
        }

    selected_repo_set = set(selected_repos)
    github_assets: list[dict] = []
    repo_assets_map: dict[str, list[dict]] = {repo: [] for repo in selected_repos}
    for asset in assets or []:
        metadata = asset.get("metadata") if isinstance(asset, dict) else None
        repo = metadata.get("repo") if isinstance(metadata, dict) else None
        if not repo or repo not in selected_repo_set:
            continue
        github_assets.append(asset)
        repo_assets_map[repo].append(asset)

    return {
        "profile": profile,
        "assets": github_assets,
        "selected_repos": selected_repos,
        "repo_assets_map": repo_assets_map,
    }


def _extract_star_candidates(raw: Any) -> list[dict]:
    """LLM JSON 응답에서 star 후보 리스트를 추출한다."""
    if isinstance(raw, dict):
        candidates = raw.get("star_candidates")
        if isinstance(candidates, list):
            return [item for item in candidates if isinstance(item, dict)]
    return []


async def _call_openai_for_star(
    profile: dict,
    assets: list[dict],
    consistency_feedback: dict | None,
) -> list[dict]:
    """LangChain(ChatOpenAI)으로 STAR 문장 후보를 생성한다."""
    llm = _build_chat_openai(temperature=0.2)
    # docs 기준: Chroma document는 summary 우선값. id 기준 추적 가능하도록 최소 필드만 전달.
    prompt_assets = [
        {
            "id": item.get("id"),
            "summary": item.get("document"),
        }
        for item in assets
    ]
    user_prompt = {
        "profile": profile,
        "assets": prompt_assets,
        "consistency_feedback": consistency_feedback or {},
    }

    response = await llm.ainvoke(
        [
            SystemMessage(content=STAR_SYSTEM_PROMPT),
            HumanMessage(content=json.dumps(user_prompt, ensure_ascii=False)),
        ]
    )
    content = response.content if isinstance(response.content, str) else "{}"
    parsed = json.loads(content)
    return _extract_star_candidates(parsed)


async def build_star_sentence(state: PortfolioState) -> dict:
    """프로필·에셋 → STAR 성과 문장 후보 생성.

    재진입 시 consistency_feedback를 프롬프트에 담아 수정 반영 재생성.

    입력: profile, assets, (재진입 시) consistency_feedback
    출력: project_candidates (repo별 STAR 후보 목록)
    """

    profile = state.get("profile") or {}
    assets = state.get("assets") or []
    feedback = state.get("consistency_feedback") or {}
    selected_repos = state.get("selected_repos") or []
    repo_assets_map = state.get("repo_assets_map") or {}

    if not profile and not assets and not repo_assets_map:
        return {
            "error": "insufficient_context_for_star",
            "project_candidates": [],
        }

    project_candidates: list[dict] = []
    repo_errors: dict[str, str] = {}
    first_error_type: str | None = None
    repos_for_generation = selected_repos or list(repo_assets_map.keys())
    for repo in repos_for_generation:
        repo_assets = repo_assets_map.get(repo) or []
        if not repo_assets:
            repo_errors[repo] = "no_assets"
            continue

        repo_feedback = feedback
        if isinstance(feedback, dict) and isinstance(feedback.get(repo), dict):
            repo_feedback = feedback[repo]

        try:
            star_candidates = await _call_openai_for_star(profile, repo_assets, repo_feedback)
        except Exception as exc:
            error_type = type(exc).__name__
            repo_errors[repo] = error_type
            if first_error_type is None:
                first_error_type = error_type
            continue
        project_candidates.append(
            {
                "repo": repo,
                "star_candidates": star_candidates,
            }
        )

    if not project_candidates:
        if first_error_type:
            return {
                "error": f"build_star_sentence_failed: {first_error_type}",
                "project_candidates": [],
                "repo_errors": repo_errors,
            }
        return {
            "error": "insufficient_context_for_star",
            "project_candidates": [],
            "repo_errors": repo_errors,
        }

    result = {"project_candidates": project_candidates}
    if repo_errors:
        result["repo_errors"] = repo_errors
    return result


def _extract_consistency_result(raw: Any) -> dict:
    """LLM JSON 응답에서 consistency 판정 결과를 추출한다."""
    if not isinstance(raw, dict):
        return {}

    feedback = raw.get("consistency_feedback")
    if not isinstance(feedback, dict):
        feedback = {}

    return {
        # True means hallucination exists.
        "is_hallucination": bool(raw.get("is_hallucination", False)),
        "is_star": bool(raw.get("is_star", False)),
        "consistency_feedback": feedback,
    }


async def _call_openai_for_consistency(
    profile: dict,
    assets: list[dict],
    star: list[dict],
) -> dict:
    """LangChain(ChatOpenAI)으로 STAR consistency를 검증한다."""
    llm = _build_chat_openai(temperature=0.0)

    prompt_assets = [
        {"id": item.get("id"), "summary": item.get("document")}
        for item in assets
    ]
    user_prompt = {
        "profile": profile,
        "assets": prompt_assets,
        "star_candidates": star,
    }

    response = await llm.ainvoke(
        [
            SystemMessage(content=CONSISTENCY_SYSTEM_PROMPT),
            HumanMessage(content=json.dumps(user_prompt, ensure_ascii=False)),
        ]
    )
    content = response.content if isinstance(response.content, str) else "{}"
    parsed = json.loads(content)
    return _extract_consistency_result(parsed)


async def self_consistency(state: PortfolioState) -> dict:
    """환각 체크 + STAR 충실도 평가.

    실패 시 consistency_feedback 기록, star_retry_count 증가 → build_star_sentence 재호출.
    LangGraph 활용 핵심: 검증 실패 시 피드백을 프롬프트에 반영해 재생성 루프.

    입력: project_candidates, profile, assets, star_retry_count
    출력: is_hallucination(환각 존재 여부), is_star, (실패 시) consistency_feedback, star_retry_count+1
    """
    project_candidates = state.get("project_candidates") or []
    star_candidates = [
        item
        for project in project_candidates
        for item in (project.get("star_candidates") or [])
        if isinstance(item, dict)
    ]
    profile = state.get("profile") or {}
    assets = state.get("assets") or []
    retry_count = state.get("star_retry_count") or 0

    if not star_candidates:
        return {
            "is_hallucination": False,
            "is_star": False,
            "consistency_feedback": {
                "hallucination": [{"reason": "STAR 문장이 없습니다. 프로필·에셋 기반으로 생성해 주세요."}],
                "star_fidelity": [],
            },
            "star_retry_count": retry_count + 1,
        }

    try:
        result = await _call_openai_for_consistency(profile, assets, star_candidates)
    except Exception as exc:
        return {
            "is_hallucination": False,
            "is_star": False,
            "consistency_feedback": {
                "hallucination": [
                    {
                        "reason": f"consistency_validation_unavailable: {type(exc).__name__}",
                    }
                ],
                "star_fidelity": [],
            },
            "star_retry_count": retry_count + 1,
        }

    is_hallucination = result.get("is_hallucination", False)
    is_star = result.get("is_star", False)
    consistency_feedback = result.get("consistency_feedback") or {}

    # pass condition: no hallucination + STAR completeness
    if (not is_hallucination) and is_star:
        return {
            "is_hallucination": False,
            "is_star": True,
            "consistency_feedback": {},
            "star_retry_count": retry_count,
        }

    if not consistency_feedback:
        consistency_feedback = {
            "hallucination": [],
            "star_fidelity": [{"reason": "검증 실패: 보완 후 재생성이 필요합니다."}],
        }

    return {
        "is_hallucination": is_hallucination,
        "is_star": is_star,
        "consistency_feedback": consistency_feedback,
        "star_retry_count": retry_count + 1,
    }


def _normalize_star_candidate(raw_star: Any) -> dict | None:
    """STAR 후보를 필수 필드 기준으로 정규화한다."""
    if not isinstance(raw_star, dict):
        return None

    normalized: dict[str, str] = {}
    for key in ("situation", "task", "action", "result"):
        value = raw_star.get(key)
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        normalized[key] = text
    return normalized


def _build_repo_intro(repo: str, stars: list[dict]) -> str:
    """레포별 간단 소개 문장을 생성한다."""
    if not stars:
        return "해당 레포의 핵심 기여를 요약할 근거 STAR가 부족합니다."

    first = stars[0]
    return (
        f"{repo}에서 {first['action']}을 수행해 "
        f"{first['result']}를 만든 프로젝트입니다."
    )


def build_portfolio(state: PortfolioState) -> dict:
    """검증된 STAR·프로필·에셋 → 포트폴리오.

    입력: star, profile, assets
    출력: portfolio
    """
    profile = state.get("profile") or {}
    selected_repos = state.get("selected_repos") or []
    project_candidates = state.get("project_candidates") or []

    repo_to_stars: dict[str, list[dict]] = {repo: [] for repo in selected_repos}
    for project in project_candidates:
        if not isinstance(project, dict):
            continue
        repo = project.get("repo")
        if not isinstance(repo, str) or not repo:
            continue
        repo_to_stars.setdefault(repo, [])

        for raw_star in project.get("star_candidates") or []:
            normalized_star = _normalize_star_candidate(raw_star)
            if normalized_star:
                repo_to_stars[repo].append(normalized_star)

    projects: list[dict] = []
    for repo in selected_repos:
        stars = repo_to_stars.get(repo, [])
        projects.append(
            {
                "repo": repo,
                "intro": _build_repo_intro(repo, stars),
                "stars": stars,
            }
        )

    github_username = (
        str(profile.get("github_username") or profile.get("id") or "developer").strip()
    )
    portfolio = {
        "title": f"{github_username} 포트폴리오",
        "summary": f"선택한 {len(selected_repos)}개 레포 기반 프로젝트 요약입니다.",
        "projects": projects,
    }
    return {"portfolio": portfolio}
