"""POST /api/cover-letter/draft — 세션·Writer 그래프·draft 저장 mock.

구현 전: ``src/api/cover_letter.py`` 가 없으면 autouse fixture 가 실패한다 (RED).
구현 후: 동일 테스트로 API 동작을 검증한다.

구현 시 참고할 패치 지점(테스트와 이름 맞출 것):

- ``build_writer_graph`` — Writer 그래프 팩토리
- ``persist_draft_records`` — drafts INSERT 대체 (AsyncMock, 실제 DB 미사용)
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from base64 import b64encode
from typing import Any, Dict
from unittest.mock import AsyncMock

import pytest
from itsdangerous import TimestampSigner
from starlette.testclient import TestClient

from src.app.main import create_app
from src.db.sqlite import connect, create_all_tables_async


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@pytest.fixture(autouse=True)
def _require_cover_letter_module() -> None:
    import importlib.util

    if importlib.util.find_spec("src.api.cover_letter") is None:
        pytest.fail(
            "Implement src/api/cover_letter.py and register the router on the app "
            "(see tests/api/test_cover_letter.py)."
        )


def _set_session(client: TestClient, data: Dict[str, Any]) -> None:
    secret_key = os.getenv("SESSION_SECRET", "dev-secret")
    payload = b64encode(json.dumps(data).encode("utf-8"))
    signed = TimestampSigner(secret_key).sign(payload).decode("utf-8")
    client.cookies.set("session", signed, path="/")


@pytest.fixture
def tmp_db(monkeypatch: pytest.MonkeyPatch, tmp_path):
    db_path = tmp_path / "cover_letter_test.db"
    monkeypatch.setenv("SQLITE_DB_PATH", str(db_path))

    async def setup() -> None:
        conn = await connect(db_path)
        await create_all_tables_async(conn)
        await conn.execute(
            """
            INSERT INTO users (id, github_username, access_token, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("u1", "testlogin", "tok", "2026-03-01", "2026-03-01"),
        )
        await conn.execute(
            """
            INSERT INTO selected_repos (user_id, repo_full_name, created_at)
            VALUES (?, ?, ?)
            """,
            ("u1", "owner/repo-a", "2026-03-01"),
        )
        await conn.execute(
            """
            INSERT INTO selected_repos (user_id, repo_full_name, created_at)
            VALUES (?, ?, ?)
            """,
            ("u1", "owner/repo-b", "2026-03-01"),
        )
        await conn.commit()
        await conn.close()

    _run(setup())
    return db_path


@pytest.fixture
def draft_client(monkeypatch: pytest.MonkeyPatch, tmp_db) -> TestClient:
    """create_app()에 등록된 cover-letter 라우터로 TestClient."""
    monkeypatch.setattr(
        "src.api.cover_letter.ensure_selected_repos_embedded",
        AsyncMock(return_value=None),
    )
    return TestClient(create_app())


def body_error_or_message(r) -> bool:
    j = r.json()
    return "error" in j or "message" in j or "detail" in j


def test_draft_unauthorized(draft_client: TestClient) -> None:
    r = draft_client.post("/api/cover-letter/draft", json={"questions": [{"question_text": "Q", "max_chars": 100}]})
    assert r.status_code == 401
    body = r.json()
    assert body.get("error") == "UNAUTHORIZED"


def test_draft_empty_questions(draft_client: TestClient) -> None:
    _set_session(draft_client, {"user_id": "u1"})
    r = draft_client.post("/api/cover-letter/draft", json={"questions": []})
    assert r.status_code == 400
    assert body_error_or_message(r)


def test_draft_missing_questions_field(draft_client: TestClient) -> None:
    _set_session(draft_client, {"user_id": "u1"})
    r = draft_client.post("/api/cover-letter/draft", json={})
    assert r.status_code == 400
    assert body_error_or_message(r)


def test_draft_success_single_question(draft_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeGraph:
        async def ainvoke(self, state: dict) -> dict:
            return {
                "draft": "테스트 초안",
                "assets": [
                    {"id": "a", "metadata": {"repo": "owner/repo-a"}},
                    {"id": "b", "metadata": {"repo": "owner/repo-a"}},
                    {"id": "c", "metadata": {"repo": "owner/repo-b"}},
                ],
                "samples": [
                    {
                        "id": "s1",
                        "company": "SK플래닛",
                        "position": "신입 앱개발자",
                        "question": "개발 역량을 보여줄 수 있는 프로젝트를 서술하세요.",
                    }
                ],
            }

    monkeypatch.setattr("src.api.cover_letter.build_writer_graph", lambda: FakeGraph())
    monkeypatch.setattr(
        "src.api.cover_letter.persist_draft_records",
        AsyncMock(
            return_value=[
                {
                    "draft_id": "d1",
                    "question_text": "지원 동기를 작성해주세요.",
                    "answer": "테스트 초안",
                    "char_count": len("테스트 초안"),
                }
            ]
        ),
    )

    _set_session(draft_client, {"user_id": "u1"})
    r = draft_client.post(
        "/api/cover-letter/draft",
        json={
            "questions": [
                {"question_text": "지원 동기를 작성해주세요.", "max_chars": 1500},
            ]
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert "drafts" in body
    assert len(body["drafts"]) == 1
    d0 = body["drafts"][0]
    assert d0.get("draft_id")
    assert d0.get("question_text") == "지원 동기를 작성해주세요."
    assert d0.get("answer") == "테스트 초안"
    assert d0.get("char_count") == len("테스트 초안")
    assert "used_assets" in body
    ua = body["used_assets"]
    assert ua.get("accepted_essays_used") is True
    essays = ua.get("accepted_essays") or []
    assert len(essays) == 1
    assert essays[0].get("company") == "SK플래닛"
    assert essays[0].get("position") == "신입 앱개발자"
    assert "개발 역량" in (essays[0].get("question") or "")
    gh = ua.get("github_repos") or []
    assert len(gh) == 2
    names = sorted(x.get("full_name") for x in gh if isinstance(x, dict))
    assert names == ["owner/repo-a", "owner/repo-b"]
    assert "created_at" in body


def test_draft_success_with_job_id(draft_client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_db) -> None:
    """jobs 테이블에 행이 있으면 그 내용으로 job_parsed 가 채워지고, 없으면 {} 로 그래프에 전달된다."""

    job_id = "job_test_1"

    async def setup_job() -> None:
        conn = await connect(tmp_db)
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
                "https://example.com/job",
                "업무",
                "자격",
                "우대",
                "ACME",
                "가치",
                "백엔드",
                "2026-03-01",
            ),
        )
        await conn.commit()
        await conn.close()

    _run(setup_job())

    expected_job_parsed = {
        "company_name": "ACME",
        "company_values": "가치",
        "position": "백엔드",
        "duty": "업무",
        "qualifications": "자격",
        "preferred": "우대",
    }

    captured: dict[str, Any] = {}

    class FakeGraph:
        async def ainvoke(self, state: dict) -> dict:
            captured["job_parsed"] = state.get("job_parsed")
            return {"draft": "x", "assets": [], "samples": []}

    monkeypatch.setattr("src.api.cover_letter.build_writer_graph", lambda: FakeGraph())
    monkeypatch.setattr(
        "src.api.cover_letter.persist_draft_records",
        AsyncMock(
            return_value=[
                {
                    "draft_id": str(uuid.uuid4()),
                    "question_text": "Q",
                    "answer": "x",
                    "char_count": 1,
                }
            ]
        ),
    )

    _set_session(draft_client, {"user_id": "u1"})
    r = draft_client.post(
        "/api/cover-letter/draft",
        json={
            "job_id": job_id,
            "questions": [{"question_text": "Q", "max_chars": 100}],
        },
    )
    assert r.status_code == 200, r.text
    assert captured.get("job_parsed") == expected_job_parsed
    ua0 = r.json()["used_assets"]
    assert ua0["accepted_essays_used"] is False
    assert ua0.get("accepted_essays") == []
    assert ua0["github_repos"] == []

    captured.clear()

    monkeypatch.setattr(
        "src.api.cover_letter.persist_draft_records",
        AsyncMock(
            return_value=[
                {
                    "draft_id": "d2",
                    "question_text": "Q2",
                    "answer": "y",
                    "char_count": 1,
                }
            ]
        ),
    )

    missing_job = "job_missing_xyz"
    r2 = draft_client.post(
        "/api/cover-letter/draft",
        json={
            "job_id": missing_job,
            "questions": [{"question_text": "Q2", "max_chars": 100}],
        },
    )
    assert r2.status_code == 200, r2.text
    assert captured.get("job_parsed") == {}


def test_draft_success_multiple_questions(draft_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict] = []
    n = [0]

    class FakeGraph:
        async def ainvoke(self, state: dict) -> dict:
            calls.append(dict(state))
            q = state.get("question", "")
            n[0] += 1
            return {
                "draft": f"답-{q[:4]}",
                "assets": [{"metadata": {"repo": f"o/r-{n[0]}"}}],
                "samples": [] if n[0] > 1 else [{"x": 1}],
            }

    async def fake_persist(_user_id: str, rows: list[dict]) -> list[dict]:
        out: list[dict] = []
        for i, row in enumerate(rows):
            qt = row["question_text"]
            ans = f"답-{qt[:4]}"
            out.append(
                {
                    "draft_id": f"id-{i}",
                    "question_text": qt,
                    "answer": ans,
                    "char_count": len(ans),
                }
            )
        return out

    monkeypatch.setattr("src.api.cover_letter.build_writer_graph", lambda: FakeGraph())
    monkeypatch.setattr("src.api.cover_letter.persist_draft_records", fake_persist)

    _set_session(draft_client, {"user_id": "u1"})
    questions = [
        {"question_text": "A", "max_chars": 100},
        {"question_text": "B", "max_chars": 100},
        {"question_text": "C", "max_chars": 100},
    ]
    r = draft_client.post("/api/cover-letter/draft", json={"questions": questions})
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["drafts"]) == 3
    assert len(calls) == 3
    assert [c.get("primary_repo") for c in calls] == [
        "owner/repo-a",
        "owner/repo-b",
        "owner/repo-a",
    ]
    ua = body["used_assets"]
    assert ua["accepted_essays_used"] is True
    assert ua.get("accepted_essays") == []
    gh = sorted(x["full_name"] for x in ua["github_repos"])
    assert gh == ["o/r-1", "o/r-2", "o/r-3"]


def test_draft_graph_error_returns_partial(draft_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeGraph:
        async def ainvoke(self, state: dict) -> dict:
            return {"error": "no_github_assets", "draft": "", "assets": [], "samples": []}

    monkeypatch.setattr("src.api.cover_letter.build_writer_graph", lambda: FakeGraph())
    monkeypatch.setattr(
        "src.api.cover_letter.persist_draft_records",
        AsyncMock(
            return_value=[
                {
                    "draft_id": "e1",
                    "question_text": "Q",
                    "answer": "",
                    "char_count": 0,
                }
            ]
        ),
    )

    _set_session(draft_client, {"user_id": "u1"})
    r = draft_client.post(
        "/api/cover-letter/draft",
        json={"questions": [{"question_text": "Q", "max_chars": 50}]},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["drafts"][0].get("answer") == ""
    assert body["used_assets"]["github_repos"] == []
    assert body["used_assets"]["accepted_essays_used"] is False
    assert body["used_assets"].get("accepted_essays") == []


@pytest.mark.asyncio
async def test_ensure_selected_repos_embedded_invokes_job_when_chroma_empty(
    monkeypatch: pytest.MonkeyPatch, tmp_db
) -> None:
    monkeypatch.setattr("src.api.cover_letter._repo_has_embedding_docs", lambda _u, _r: False)
    monkeypatch.setattr(
        "src.api.cover_letter.fetch_code_document_ids_for_repo",
        AsyncMock(return_value=["owner/repo-a/foo.py"]),
    )
    mock_job = AsyncMock(return_value={"embedded": 1})
    monkeypatch.setattr("src.api.cover_letter.run_github_repo_embedding_job", mock_job)

    from src.api.cover_letter import ensure_selected_repos_embedded

    await ensure_selected_repos_embedded("u1", ["owner/repo-a"])
    mock_job.assert_awaited_once()
    assert mock_job.await_args.kwargs["user_id"] == "u1"
    assert mock_job.await_args.kwargs["repo_full_name"] == "owner/repo-a"
    assert mock_job.await_args.kwargs["code_document_ids"] == ["owner/repo-a/foo.py"]
