"""2번 그래프(Writer) 노드."""

from __future__ import annotations

import json
import os
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.service.rag import retrieve_passed_cover_letters, retrieve_user_assets

from .prompts import DRAFT_CONSISTENCY_SYSTEM_PROMPT, DRAFT_SYSTEM_PROMPT
from .state import WriterState

DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def _build_chat_openai(temperature: float) -> ChatOpenAI:
    """ChatOpenAI JSON mode (portfolio_graph/node.py와 동일 패턴)."""
    return ChatOpenAI(
        model=DEFAULT_MODEL,
        temperature=temperature,
        api_key=os.getenv("OPENAI_API_KEY"),
        model_kwargs={"response_format": {"type": "json_object"}},
    )


def _question_missing(state: WriterState) -> bool:
    q = state.get("question")
    if q is None:
        return True
    if isinstance(q, str) and not q.strip():
        return True
    return False


def _max_chars_missing(state: WriterState) -> bool:
    return state.get("max_chars") is None


def _job_parsed_meta(job_parsed: dict | None) -> tuple[str | None, str | None, str | None]:
    if not isinstance(job_parsed, dict):
        return None, None, None
    company = job_parsed.get("company_name")
    position = job_parsed.get("position")
    year = job_parsed.get("year")
    if year is not None and not isinstance(year, str):
        year = str(year)
    if isinstance(company, str) and not company.strip():
        company = None
    if isinstance(position, str) and not position.strip():
        position = None
    if isinstance(year, str) and not year.strip():
        year = None
    return (
        str(company) if company is not None else None,
        str(position) if position is not None else None,
        year,
    )


def _summarize_assets(assets: list[Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in assets or []:
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "id": item.get("id"),
                "summary": item.get("document"),
                "metadata": item.get("metadata"),
            }
        )
    return out


async def retrieve_samples(state: WriterState) -> dict:
    """진입 시 검증 + 합격 자소서 검색 모듈 호출."""
    if _question_missing(state):
        return {"error": "question is required"}
    if _max_chars_missing(state):
        return {"error": "max_chars is required"}

    job = state.get("job_parsed") if isinstance(state.get("job_parsed"), dict) else {}
    company_name, position, year = _job_parsed_meta(job)
    question = str(state.get("question", "")).strip()

    try:
        samples = await retrieve_passed_cover_letters(
            question=question,
            company_name=company_name,
            position=position,
            year=year,
            top_k=5,
        )
    except Exception:
        samples = []

    return {"samples": samples}


async def load_assets(state: WriterState) -> dict:
    """유저 DB에서 에셋 조회."""
    user_id = state.get("user_id")
    if not user_id:
        return {"error": "user_id is required"}

    try:
        # user_assets_{user_id} 는 현재 GitHub 임베딩만 적재. 과거 문서는 source 메타가 없을 수 있어
        # source_filter 를 쓰면 0건이 되어 no_github_assets 가 나므로 필터 없이 조회한다.
        assets = await retrieve_user_assets(
            user_id=str(user_id),
            source_filter=None,
            type_filter=None,
            top_k=20,
        )
    except Exception as exc:
        return {"error": f"retrieve_user_assets_failed: {type(exc).__name__}", "assets": []}

    if not assets:
        return {"error": "no_github_assets", "assets": []}

    return {"assets": assets}


async def generate_draft(state: WriterState) -> dict:
    """LLM 초안 생성."""
    llm = _build_chat_openai(temperature=0.2)

    assets = _summarize_assets(state.get("assets") or [])
    user_payload: dict[str, Any] = {
        "question": state.get("question"),
        "max_chars": state.get("max_chars"),
        "job_parsed": state.get("job_parsed") or {},
        "assets": assets,
        "samples": state.get("samples") or [],
    }
    human_text = json.dumps(user_payload, ensure_ascii=False)
    feedback = state.get("consistency_feedback")
    if feedback:
        human_text += (
            "\n\n다음 지적사항을 반영해 수정해줘: "
            + (
                json.dumps(feedback, ensure_ascii=False)
                if isinstance(feedback, (dict, list))
                else str(feedback)
            )
        )

    try:
        response = await llm.ainvoke(
            [
                SystemMessage(content=DRAFT_SYSTEM_PROMPT),
                HumanMessage(content=human_text),
            ]
        )
        content = response.content if isinstance(response.content, str) else "{}"
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            draft = parsed.get("draft")
            if isinstance(draft, str):
                return {"draft": draft}
    except Exception:
        pass

    return {"draft": ""}


async def self_consistency(state: WriterState) -> dict:
    """환각 체크."""
    llm = _build_chat_openai(temperature=0.0)
    draft = state.get("draft") or ""
    assets = _summarize_assets(state.get("assets") or [])
    retry = state.get("draft_retry_count") or 0

    user_payload = {
        "draft": draft,
        "assets": assets,
    }
    try:
        response = await llm.ainvoke(
            [
                SystemMessage(content=DRAFT_CONSISTENCY_SYSTEM_PROMPT),
                HumanMessage(content=json.dumps(user_payload, ensure_ascii=False)),
            ]
        )
        content = response.content if isinstance(response.content, str) else "{}"
        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            return {
                "is_hallucination": False,
                "consistency_feedback": {},
                "draft_retry_count": retry,
            }

        is_hallucination = bool(parsed.get("is_hallucination", False))
        raw_fb = parsed.get("consistency_feedback")
        if not isinstance(raw_fb, dict):
            raw_fb = {}

        if not is_hallucination:
            return {
                "is_hallucination": False,
                "consistency_feedback": {},
                "draft_retry_count": retry,
            }

        return {
            "is_hallucination": True,
            "consistency_feedback": raw_fb,
            "draft_retry_count": retry + 1,
        }
    except Exception:
        return {
            "is_hallucination": False,
            "consistency_feedback": {},
            "draft_retry_count": retry,
        }


def format_output(state: WriterState) -> dict:
    """글자수·형식 정리."""
    draft = state.get("draft") or ""
    if state.get("max_chars") is not None:
        mc = int(state["max_chars"])
        draft = draft[:mc]
        draft = re.sub(r"\n\n+", "\n", draft)
        draft = draft.strip()
    else:
        draft = draft.strip()
    return {"draft": draft}
