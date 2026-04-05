"""
자소서 Draft API (Writer 그래프).

POST /api/cover-letter/draft — 문항별 초안 생성 및 drafts 테이블 저장.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any

import aiosqlite
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from src.db.sqlite.client import connect
from src.db.vector import get_user_asset_collection
from src.graphs.inspector_graph import build_inspector_graph
from src.graphs.inspector_graph.edge import MAX_ROUNDS
from src.graphs.writer_graph import build_writer_graph
from src.service.github_embedding.hierarchy import fetch_code_document_ids_for_repo
from src.service.github_embedding.service import run_github_repo_embedding_job
from src.service.user.repos import get_selected_repos

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


class InspectRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    draft_id: str
    """Writer 저장 draft 행 id."""

    user_edited: str | None = None
    """비어 있으면 DB 초안으로 첫 Inspector. 값이 있으면 수정본 기준 재첨삭."""

    round: int = 0
    """첨삭 라운드(프롬프트·문서 MAX_ROUNDS와 정합). 0=Writer 직후 첫 분석."""


def _repo_has_embedding_docs(user_id: str, repo_full_name: str) -> bool:
    """Chroma user_assets_{user_id}에 해당 repo 문서가 하나라도 있는지."""
    try:
        col = get_user_asset_collection(user_id)
        out = col.get(where={"repo": {"$eq": repo_full_name}}, limit=1)
        ids = out.get("ids") or []
        return len(ids) > 0
    except Exception:
        return False


async def _fetch_user_access_token(user_id: str) -> str | None:
    conn = await connect()
    try:
        cur = await conn.execute("SELECT access_token FROM users WHERE id = ?", (user_id,))
        row = await cur.fetchone()
        await cur.close()
        if not row or not row["access_token"]:
            return None
        return str(row["access_token"])
    finally:
        await conn.close()


async def ensure_selected_repos_embedded(user_id: str, repo_full_names: list[str]) -> None:
    """선택 레포 중 Chroma에 없는 레포는 asset_hierarchy·토큰이 있으면 임베딩 잡을 돌린다."""
    for full_name in repo_full_names:
        has_docs = await asyncio.to_thread(_repo_has_embedding_docs, user_id, full_name)
        if has_docs:
            continue
        code_ids = await fetch_code_document_ids_for_repo(user_id, full_name)
        if not code_ids:
            continue
        token = await _fetch_user_access_token(user_id)
        if not token:
            continue
        await run_github_repo_embedding_job(
            user_id=user_id,
            access_token=token,
            repo_full_name=full_name,
            code_document_ids=code_ids,
        )


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


async def fetch_draft_row(user_id: str, draft_id: str) -> dict[str, Any] | None:
    """drafts 단건 조회 (해당 user_id만)."""
    conn = await connect()
    try:
        cur = await conn.execute(
            """
            SELECT id, user_id, job_id, question_text, max_chars, answer, round
            FROM drafts
            WHERE id = ? AND user_id = ?
            """,
            (draft_id, user_id),
        )
        row = await cur.fetchone()
        await cur.close()
        if not row:
            return None
        return {
            "id": row["id"],
            "user_id": row["user_id"],
            "job_id": row["job_id"],
            "question_text": row["question_text"],
            "max_chars": row["max_chars"],
            "answer": row["answer"],
            "round": row["round"],
        }
    finally:
        await conn.close()


def _accepted_essay_item(sample: dict[str, Any]) -> dict[str, str] | None:
    """samples 항목에서 company·position·question 추출 (metadata 우선, 없으면 최상위)."""
    meta = sample.get("metadata") if isinstance(sample.get("metadata"), dict) else {}

    def _pick(key: str) -> str:
        for src in (meta, sample):
            v = src.get(key)
            if v is not None and str(v).strip():
                return str(v).strip()
        return ""

    company = _pick("company")
    position = _pick("position")
    question = _pick("question")
    if not company and not position and not question:
        return None
    return {"company": company, "position": position, "question": question}


def _used_assets_from_graph_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    """ainvoke 결과 목록으로 used_assets 응답 객체를 만든다 (문항 다건 시 병합)."""
    repos_seen: set[str] = set()
    github_repos: list[dict[str, str]] = []
    accepted_essays_used = False
    essay_keys: set[tuple[str, str, str]] = set()
    accepted_essays: list[dict[str, str]] = []

    for result in results:
        samples = result.get("samples") or []
        if len(samples) > 0:
            accepted_essays_used = True
        for s in samples:
            if not isinstance(s, dict):
                continue
            item = _accepted_essay_item(s)
            if item is None:
                continue
            key = (item["company"], item["position"], item["question"])
            if key in essay_keys:
                continue
            essay_keys.add(key)
            if len(accepted_essays) < 3:
                accepted_essays.append(item)

        assets = result.get("assets") or []
        for a in assets:
            if not isinstance(a, dict):
                continue
            meta = a.get("metadata")
            if not isinstance(meta, dict):
                meta = {}
            repo = meta.get("repo")
            if repo and isinstance(repo, str) and repo not in repos_seen:
                repos_seen.add(repo)
                github_repos.append({"full_name": repo})
    return {
        "github_repos": github_repos,
        "accepted_essays_used": accepted_essays_used,
        "accepted_essays": accepted_essays,
    }


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

    try:
        selected_repos = await get_selected_repos(user_id)
    except Exception:
        selected_repos = []

    await ensure_selected_repos_embedded(user_id, selected_repos)

    rotation = selected_repos[:3] if selected_repos else []

    graph = build_writer_graph()
    answers: list[str] = []
    graph_results: list[dict[str, Any]] = []

    for idx, q in enumerate(body.questions):
        primary_repo = ""
        if rotation:
            primary_repo = rotation[idx % len(rotation)]
        state: dict[str, Any] = {
            "user_id": user_id,
            "primary_repo": primary_repo,
            "question": q.question_text,
            "max_chars": q.max_chars,
            "job_parsed": job_parsed,
            "samples": [],
            "assets": [],
        }
        result = await graph.ainvoke(state)
        graph_results.append(result)
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

    used_assets = _used_assets_from_graph_results(graph_results)

    return {
        "drafts": drafts,
        "used_assets": used_assets,
        "created_at": now,
    }


@router.post("/inspect", response_model=None)
async def inspect_cover_letter(request: Request, body: InspectRequest) -> JSONResponse | dict[str, Any]:
    """Writer 저장 draft에 대해 Inspector 그래프를 한 번 실행해 보완 제안을 반환한다.

    첫 호출: ``user_edited`` 생략(또는 빈 문자열) — DB ``answer`` 기준.
    재첨삭: 수정본을 ``user_edited``로 보내고 ``round``를 1씩 올린다 (0 ≤ round < MAX_ROUNDS).
    """
    user_id = request.session.get("user_id")
    if not user_id:
        return _error_response(401, "UNAUTHORIZED", "UNAUTHORIZED")

    user_id = str(user_id)
    if body.round < 0 or body.round >= MAX_ROUNDS:
        return _error_response(400, "BAD_REQUEST", "INSPECT_ROUND_OUT_OF_RANGE")

    draft_id = (body.draft_id or "").strip()
    if not draft_id:
        return _error_response(400, "BAD_REQUEST", "DRAFT_ID_REQUIRED")

    row = await fetch_draft_row(user_id, draft_id)
    if row is None:
        return _error_response(404, "NOT_FOUND", "DRAFT_NOT_FOUND")

    job_id_val = row.get("job_id")
    job_id_str = str(job_id_val) if job_id_val is not None else None
    job_parsed, _ = await fetch_job_context(job_id_str)

    try:
        selected_repos = await get_selected_repos(user_id)
    except Exception:
        selected_repos = []

    await ensure_selected_repos_embedded(user_id, selected_repos)

    edited = (body.user_edited or "").strip()
    answer = (row.get("answer") or "") if isinstance(row.get("answer"), str) else ""
    if not isinstance(answer, str):
        answer = str(answer or "")

    if edited:
        init_state: dict[str, Any] = {
            "user_id": user_id,
            "question": str(row.get("question_text") or ""),
            "job_parsed": job_parsed,
            "draft": "",
            "user_edited": edited,
            "round": body.round,
        }
    else:
        init_state = {
            "user_id": user_id,
            "question": str(row.get("question_text") or ""),
            "job_parsed": job_parsed,
            "draft": answer,
            "user_edited": "",
            "round": body.round,
        }

    if not edited and not (answer or "").strip():
        return _error_response(400, "BAD_REQUEST", "EMPTY_DRAFT")

    graph = build_inspector_graph()
    result = await graph.ainvoke(init_state)

    err = result.get("error")
    if err:
        msg = str(err).strip() or "INSPECTOR_FAILED"
        if len(msg) > 400:
            msg = msg[:397] + "..."
        return _error_response(400, "BAD_REQUEST", msg)

    suggestions = result.get("suggestions")
    if not isinstance(suggestions, list):
        suggestions = []

    return {
        "draft_id": draft_id,
        "round": body.round,
        "max_rounds": MAX_ROUNDS,
        "suggestions": suggestions,
    }
