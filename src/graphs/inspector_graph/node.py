"""3번 그래프(Inspector) 노드."""

from __future__ import annotations

import json
import os
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from src.service.rag import retrieve_passed_cover_letters, retrieve_user_assets

from .prompts import INSPECTOR_SYSTEM_PROMPT, build_inspector_user_prompt
from .state import InspectorState

DEFAULT_INSPECTOR_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


def _stub_suggestions() -> list[dict[str, str]]:
    """OPENAI_API_KEY 없음·파싱 실패 시 결정적 스텁 (CI/로컬)."""
    return [
        {
            "section": "전체",
            "suggestion": "OPENAI_API_KEY가 없거나 응답 파싱에 실패해 스텁 제안이 반환되었습니다.",
            "rationale": "로컬·CI에서 그래프 경로를 검증하기 위한 고정 메시지입니다.",
            "priority": "low",
        }
    ]


def _build_chat_openai(temperature: float) -> ChatOpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    return ChatOpenAI(
        model=DEFAULT_INSPECTOR_MODEL,
        temperature=temperature,
        api_key=api_key,
        model_kwargs={"response_format": {"type": "json_object"}},
    )


def _brief_documents(
    items: list[Any],
    *,
    max_items: int = 8,
    max_chars: int = 400,
) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for item in (items or [])[:max_items]:
        if not isinstance(item, dict):
            continue
        doc = item.get("document")
        text = doc if isinstance(doc, str) else (str(doc) if doc is not None else "")
        text = text.strip().replace("\n", " ")
        if len(text) > max_chars:
            text = text[: max_chars - 3] + "..."
        if text:
            out.append({"summary": text})
    return out


def _job_parsed_meta(job_parsed: dict | None) -> tuple[str | None, str | None, str | None]:
    """Writer `load_assets` / `retrieve_samples`와 동일한 job_parsed 키."""
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


def _brief_passed_samples(
    samples: list[Any],
    *,
    max_items: int = 5,
    max_chars: int = 500,
) -> list[dict[str, str]]:
    """passed_samples.retrieve_passed_cover_letters 결과(question/answer)용."""
    out: list[dict[str, str]] = []
    for item in (samples or [])[:max_items]:
        if not isinstance(item, dict):
            continue
        q = str(item.get("question") or "").strip()
        a = str(item.get("answer") or "").strip()
        text = ""
        if q and a:
            text = f"문항: {q} / 답변 요지: {a}"
        elif a:
            text = a
        elif q:
            text = q
        text = text.replace("\n", " ")
        if len(text) > max_chars:
            text = text[: max_chars - 3] + "..."
        if text:
            out.append({"summary": text})
    return out


def _normalize_suggestions(raw: Any) -> list[dict[str, str]]:
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        suggestion = str(item.get("suggestion") or "").strip()
        if not suggestion:
            continue
        out.append(
            {
                "section": str(item.get("section") or "").strip() or "기타",
                "suggestion": suggestion,
                "rationale": str(item.get("rationale") or "").strip(),
                "priority": str(item.get("priority") or "medium").strip().lower()
                or "medium",
            }
        )
    return out


async def load_draft(state: InspectorState) -> dict:
    """진입 시 검증 + 무조건 에셋·합격 샘플 재조회.

    round는 올리지 않는다 (re_inspect에서만 증가).
    state에 이미 반영된 draft를 우선하고, 비어 있을 때만 user_edited를 초안으로 쓴다.
    """
    user_id = (state.get("user_id") or "").strip()
    draft = (state.get("draft") or "").strip()
    user_edited = (state.get("user_edited") or "").strip()

    if not draft and not user_edited:
        return {"error": "draft 또는 user_edited가 필요합니다."}

    effective_draft = draft if draft else user_edited

    if not user_id:
        return {"error": "user_id is required"}

    question = state.get("question") or ""
    job = state.get("job_parsed") if isinstance(state.get("job_parsed"), dict) else {}
    company_name, position, year = _job_parsed_meta(job if job else None)

    try:
        assets = await retrieve_user_assets(
            user_id=user_id,
            source_filter=["github"],
            type_filter=["project", "folder", "code", "document"],
            top_k=20,
        )
    except Exception as exc:  # pragma: no cover - defensive path
        return {"error": f"asset retrieval failed: {type(exc).__name__}: {exc}"}

    try:
        samples = await retrieve_passed_cover_letters(
            question=str(question),
            company_name=company_name,
            position=position,
            year=year,
            top_k=5,
        )
    except Exception as exc:  # pragma: no cover - defensive path
        return {"error": f"sample retrieval failed: {type(exc).__name__}: {exc}"}

    return {
        "draft": effective_draft,
        "assets": assets,
        "samples": samples,
        "error": "",
    }


async def analyze(state: InspectorState) -> dict:
    """LLM 보완점 분석 → suggestions."""
    draft = state.get("draft") or ""
    assets = state.get("assets") or []
    samples = state.get("samples") or []
    question = state.get("question") or ""
    round_num = int(state.get("round") or 0)

    assets_brief = _brief_documents(assets)
    samples_brief = _brief_passed_samples(samples)

    if not os.getenv("OPENAI_API_KEY"):
        return {"suggestions": _stub_suggestions()}

    user_content = build_inspector_user_prompt(
        draft=draft,
        question=str(question),
        assets_brief=assets_brief,
        samples_brief=samples_brief,
        round_num=round_num,
    )

    try:
        llm = _build_chat_openai(temperature=0.25)
        resp = await llm.ainvoke(
            [
                SystemMessage(content=INSPECTOR_SYSTEM_PROMPT),
                HumanMessage(content=user_content),
            ]
        )
        content = resp.content
        if not isinstance(content, str):
            content = str(content)
        data = json.loads(content)
        suggestions = _normalize_suggestions(data.get("suggestions"))
        if not suggestions:
            return {"suggestions": _stub_suggestions()}
        return {"suggestions": suggestions}
    except Exception:
        return {"suggestions": _stub_suggestions()}


async def suggest(state: InspectorState) -> dict:
    """제안 반환. interrupt 지점."""
    return {"suggestions": state.get("suggestions") or []}


def re_inspect(state: InspectorState) -> dict:
    """재호출 시 user_edited → draft 갱신, round 증가.

    user_edited가 비어 있으면 상태를 바꾸지 않는다 (checkpointer 없이 suggest 직후
    END로 가는 경로에서 draft/round가 망가지지 않게 함).
    """
    user_edited = (state.get("user_edited") or "").strip()
    if not user_edited:
        return {}

    current_round = int(state.get("round") or 0)
    return {"draft": user_edited, "round": current_round + 1}
