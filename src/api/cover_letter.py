"""
자소서 Draft API (Writer 그래프).

POST /api/cover-letter/draft — 문항별 초안 생성 및 drafts 테이블 저장.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import aiosqlite
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from src.db.sqlite.client import connect
from src.graphs.writer_graph import build_writer_graph

router = APIRouter(prefix="/api/cover-letter", tags=["cover-letter"])


def _error_response(status_code: int, error: str, message: str) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": error, "message": message})


class QuestionItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    question_text: str
    max_chars: int


class DraftRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    job_id: str | None = None
    questions: list[QuestionItem] | None = None


async def fetch_job_context(job_id: str | None) -> tuple[dict[str, Any], str | None]:
    """(Writer용 job_parsed, drafts FK용 job_id). jobs 행이 없으면 ({}, None)."""
    if not job_id:
        return {}, None
    conn = await connect()
    try:
        cur = await conn.execute(
            """
            SELECT id, company_name, company_values, position, duty, qualifications, preferred
            FROM jobs
            WHERE id = ?
            """,
            (job_id,),
        )
        row = await cur.fetchone()
        await cur.close()
        if not row:
            return {}, None
        job_parsed = {
            "company_name": row["company_name"],
            "company_values": row["company_values"],
            "position": row["position"],
            "duty": row["duty"],
            "qualifications": row["qualifications"],
            "preferred": row["preferred"],
        }
        return job_parsed, row["id"]
    finally:
        await conn.close()


async def persist_draft_records(user_id: str, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """drafts 테이블에 INSERT 하고 API 응답용 drafts 항목 목록을 반환한다."""
    conn = await connect()
    try:
        out: list[dict[str, Any]] = []
        for row in rows:
            await conn.execute(
                """
                INSERT INTO drafts (
                    id, user_id, job_id, question_text, max_chars, answer, round,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["id"],
                    user_id,
                    row.get("job_id"),
                    row["question_text"],
                    row["max_chars"],
                    row["answer"],
                    row.get("round", 0),
                    row["created_at"],
                    row["updated_at"],
                ),
            )
            ans = row["answer"] or ""
            out.append(
                {
                    "draft_id": row["id"],
                    "question_text": row["question_text"],
                    "answer": ans,
                    "char_count": len(ans),
                }
            )
        await conn.commit()
        return out
    except aiosqlite.Error:
        await conn.rollback()
        raise
    finally:
        await conn.close()


@router.post("/draft", response_model=None)
async def create_cover_letter_draft(request: Request, body: DraftRequest) -> JSONResponse | dict[str, Any]:
    user_id = request.session.get("user_id")
    if not user_id:
        return _error_response(401, "UNAUTHORIZED", "UNAUTHORIZED")

    if body.questions is None or len(body.questions) == 0:
        return _error_response(400, "BAD_REQUEST", "QUESTIONS_REQUIRED")

    user_id = str(user_id)
    req_job_id = body.job_id
    job_parsed, fk_job_id = await fetch_job_context(req_job_id)

    graph = build_writer_graph()
    answers: list[str] = []

    for q in body.questions:
        state: dict[str, Any] = {
            "user_id": user_id,
            "question": q.question_text,
            "max_chars": q.max_chars,
            "job_parsed": job_parsed,
            "samples": [],
            "assets": [],
        }
        result = await graph.ainvoke(state)
        if result.get("error"):
            answers.append("")
        else:
            draft_text = result.get("draft")
            answers.append(draft_text if isinstance(draft_text, str) else "")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    rows: list[dict[str, Any]] = []
    for q, ans in zip(body.questions, answers, strict=True):
        rows.append(
            {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "job_id": fk_job_id,
                "question_text": q.question_text,
                "max_chars": q.max_chars,
                "answer": ans,
                "round": 0,
                "created_at": now,
                "updated_at": now,
            }
        )

    try:
        drafts = await persist_draft_records(user_id, rows)
    except aiosqlite.Error:
        return _error_response(500, "INTERNAL_SERVER_ERROR", "DRAFT_PERSIST_FAILED")

    return {
        "drafts": drafts,
        "used_assets": {"github_repos": [], "accepted_essays_used": False},
        "created_at": now,
    }
