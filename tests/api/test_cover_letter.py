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
        await conn.commit()
        await conn.close()

    _run(setup())
    return db_path


@pytest.fixture
def draft_client(monkeypatch: pytest.MonkeyPatch, tmp_db) -> TestClient:
    """create_app()에 등록된 cover-letter 라우터로 TestClient."""
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
            return {"draft": "테스트 초안"}

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
            return {"draft": "x"}

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

    class FakeGraph:
        async def ainvoke(self, state: dict) -> dict:
            calls.append(dict(state))
            q = state.get("question", "")
            return {"draft": f"답-{q[:4]}"}

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


def test_draft_graph_error_returns_partial(draft_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeGraph:
        async def ainvoke(self, state: dict) -> dict:
            return {"error": "no_github_assets", "draft": ""}

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
