"""
채용공고 파싱 API — jobs 테이블 저장 후 job_id 반환.

POST /api/jobs/parse — manual(직접 입력) 또는 url(크롤 + 선택적 LLM 구조화).
"""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

import aiosqlite
import httpx
from bs4 import BeautifulSoup
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict, Field

from src.db.sqlite.client import connect

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _error_response(status_code: int, error: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": error, "message": message})


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _join_lines(items: list[str] | None) -> str | None:
    if not items:
        return None
    lines = [str(x).strip() for x in items if x and str(x).strip()]
    return "\n".join(lines) if lines else None


class JobsParseBody(BaseModel):
    model_config = ConfigDict(extra="ignore")

    source_type: Literal["url", "manual"]
    url: str | None = None
    position_title: str | None = None
    company_name: str | None = None
    company_persona: str | None = None
    duties: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    preferences: list[str] = Field(default_factory=list)


async def _insert_job_row(
    *,
    job_id: str,
    url: str,
    duty: str | None,
    qualifications: str | None,
    preferred: str | None,
    company_name: str | None,
    company_values: str | None,
    position: str | None,
) -> None:
    conn = await connect()
    try:
        await conn.execute(
            """
            INSERT INTO jobs (
                id, url, duty, qualifications, preferred,
                company_name, company_values, position, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                url,
                duty,
                qualifications,
                preferred,
                company_name,
                company_values,
                position,
                _now_iso(),
            ),
        )
        await conn.commit()
    except aiosqlite.Error:
        await conn.rollback()
        raise
    finally:
        await conn.close()


async def _fetch_url_text(raw_url: str) -> tuple[str, str]:
    """(plain_text, page_title). 실패 시 예외."""
    url = raw_url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        res = await client.get(url, headers={"User-Agent": "AutofolioJobBot/1.0"})
        res.raise_for_status()
        html = res.text
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    title = (soup.title.string or "").strip() if soup.title else ""
    text = soup.get_text(separator="\n", strip=True)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text, title


def _heuristic_from_url_text(text: str, title: str) -> dict[str, Any]:
    snippet = (text or "")[:6000]
    return {
        "company_name": (title[:200] if title else "(제목 없음)"),
        "position_title": "채용공고",
        "company_persona": "",
        "duties": [snippet] if snippet else [],
        "requirements": [],
        "preferences": [],
    }


async def _llm_structure_job(text: str, url: str, title: str) -> dict[str, Any] | None:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    client = AsyncOpenAI(api_key=key)
    payload = (text or "")[:20000]
    msg = (
        f"page_title: {title}\nurl: {url}\n\nbody_text:\n{payload}"
    )
    resp = await client.chat.completions.create(
        model=os.getenv("OPENAI_JOB_PARSE_MODEL", "gpt-4o-mini"),
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You extract job posting fields from Korean or English text. "
                    "Return a single JSON object with keys: "
                    "company_name (string), position_title (string), "
                    "company_persona (string), "
                    "duties (array of short strings), "
                    "requirements (array of strings), "
                    "preferences (array of strings). "
                    "Use empty string or [] if unknown."
                ),
            },
            {"role": "user", "content": msg},
        ],
        temperature=0.2,
    )
    raw = (resp.choices[0].message.content or "").strip()
    data = json.loads(raw)
    return {
        "company_name": str(data.get("company_name") or "").strip() or "(미상)",
        "position_title": str(data.get("position_title") or "").strip() or "채용공고",
        "company_persona": str(data.get("company_persona") or "").strip(),
        "duties": [str(x).strip() for x in (data.get("duties") or []) if str(x).strip()],
        "requirements": [str(x).strip() for x in (data.get("requirements") or []) if str(x).strip()],
        "preferences": [str(x).strip() for x in (data.get("preferences") or []) if str(x).strip()],
    }


def _response_payload(
    *,
    job_id: str,
    source_type: str,
    position_title: str,
    company_name: str,
    company_persona: str,
    duties: list[str],
    requirements: list[str],
    preferences: list[str],
) -> dict[str, Any]:
    return {
        "job_id": job_id,
        "source_type": source_type,
        "position_title": position_title,
        "company_name": company_name,
        "company_persona": company_persona,
        "duties": duties,
        "requirements": requirements,
        "preferences": preferences,
        "created_at": _now_iso(),
    }


@router.post("/parse", response_model=None)
async def parse_job(request: Request, body: JobsParseBody) -> JSONResponse | dict[str, Any]:
    uid = request.session.get("user_id")
    if not uid:
        return _error_response(401, "UNAUTHORIZED", "UNAUTHORIZED")

    if body.source_type == "manual":
        if not body.position_title or not str(body.position_title).strip():
            return _error_response(400, "BAD_REQUEST", "position_title is required for manual")
        if not body.company_name or not str(body.company_name).strip():
            return _error_response(400, "BAD_REQUEST", "company_name is required for manual")

        job_id = str(uuid.uuid4())
        url = f"manual://{job_id}"
        duty = _join_lines(body.duties)
        qual = _join_lines(body.requirements)
        pref = _join_lines(body.preferences)
        persona = (body.company_persona or "").strip() or None

        try:
            await _insert_job_row(
                job_id=job_id,
                url=url,
                duty=duty,
                qualifications=qual,
                preferred=pref,
                company_name=body.company_name.strip(),
                company_values=persona,
                position=body.position_title.strip(),
            )
        except aiosqlite.Error:
            return _error_response(500, "INTERNAL_SERVER_ERROR", "JOB_PERSIST_FAILED")

        return _response_payload(
            job_id=job_id,
            source_type="manual",
            position_title=body.position_title.strip(),
            company_name=body.company_name.strip(),
            company_persona=persona or "",
            duties=list(body.duties or []),
            requirements=list(body.requirements or []),
            preferences=list(body.preferences or []),
        )

    # url
    if not body.url or not str(body.url).strip():
        return _error_response(400, "BAD_REQUEST", "url is required for source_type=url")

    try:
        text, title = await _fetch_url_text(body.url)
    except httpx.HTTPError as exc:
        return _error_response(
            400,
            "CRAWL_FAILED",
            f"HTTP fetch failed: {type(exc).__name__}: {exc}",
        )
    except Exception as exc:
        return _error_response(
            400,
            "CRAWL_FAILED",
            f"Failed to read job page: {type(exc).__name__}: {exc}",
        )

    structured: dict[str, Any] | None = None
    try:
        structured = await _llm_structure_job(text, body.url.strip(), title)
    except Exception:
        structured = None

    if structured is None:
        structured = _heuristic_from_url_text(text, title)

    job_id = str(uuid.uuid4())
    duty = _join_lines(structured.get("duties") or [])
    qual = _join_lines(structured.get("requirements") or [])
    pref = _join_lines(structured.get("preferences") or [])

    try:
        await _insert_job_row(
            job_id=job_id,
            url=body.url.strip(),
            duty=duty,
            qualifications=qual,
            preferred=pref,
            company_name=structured["company_name"],
            company_values=(structured.get("company_persona") or None),
            position=structured["position_title"],
        )
    except aiosqlite.Error:
        return _error_response(500, "INTERNAL_SERVER_ERROR", "JOB_PERSIST_FAILED")

    return _response_payload(
        job_id=job_id,
        source_type="url",
        position_title=structured["position_title"],
        company_name=structured["company_name"],
        company_persona=structured.get("company_persona") or "",
        duties=list(structured.get("duties") or []),
        requirements=list(structured.get("requirements") or []),
        preferences=list(structured.get("preferences") or []),
    )


@router.get("/recent", response_model=None)
async def list_recent_jobs(request: Request, limit: int = 30) -> JSONResponse | dict[str, Any]:
    """최근 저장된 채용공고 목록 (대시보드 job_id 선택용). 로그인 필요."""
    uid = request.session.get("user_id")
    if not uid:
        return _error_response(401, "UNAUTHORIZED", "UNAUTHORIZED")

    lim = max(1, min(int(limit), 100))
    conn = await connect()
    try:
        cur = await conn.execute(
            """
            SELECT id, company_name, position, url, created_at
            FROM jobs
            ORDER BY datetime(created_at) DESC
            LIMIT ?
            """,
            (lim,),
        )
        rows = await cur.fetchall()
        await cur.close()
    finally:
        await conn.close()

    jobs: list[dict[str, Any]] = []
    for row in rows:
        jobs.append(
            {
                "id": row["id"],
                "company_name": row["company_name"],
                "position": row["position"],
                "url": row["url"],
                "created_at": row["created_at"],
            }
        )
    return {"jobs": jobs}
