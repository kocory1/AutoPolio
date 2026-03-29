"""POST /api/jobs/parse — 세션·manual·url."""

from __future__ import annotations

import asyncio
import json
import os
from base64 import b64encode
from typing import Any, Dict

import httpx
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


def _set_session(client: TestClient, data: Dict[str, Any]) -> None:
    secret_key = os.getenv("SESSION_SECRET", "dev-secret")
    payload = b64encode(json.dumps(data).encode("utf-8"))
    signed = TimestampSigner(secret_key).sign(payload).decode("utf-8")
    client.cookies.set("session", signed, path="/")


@pytest.fixture
def client(tmp_path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    db_path = tmp_path / "jobs_test.db"
    monkeypatch.setenv("SQLITE_DB_PATH", str(db_path))

    async def setup() -> None:
        conn = await connect(db_path)
        await create_all_tables_async(conn)
        await conn.commit()
        await conn.close()

    _run(setup())
    return TestClient(create_app())


def test_jobs_parse_unauthorized(client: TestClient) -> None:
    r = client.post("/api/jobs/parse", json={"source_type": "manual", "company_name": "A", "position_title": "B"})
    assert r.status_code == 401


def test_jobs_parse_manual_success(client: TestClient) -> None:
    _set_session(client, {"user_id": "u1"})
    r = client.post(
        "/api/jobs/parse",
        json={
            "source_type": "manual",
            "company_name": "ACME",
            "position_title": "백엔드",
            "company_persona": "협업",
            "duties": ["API 설계", "운영"],
            "requirements": ["Python"],
            "preferences": ["RAG"],
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("job_id")
    assert body.get("company_name") == "ACME"
    assert body.get("position_title") == "백엔드"
    assert len(body.get("duties", [])) == 2


def test_jobs_parse_manual_missing_company(client: TestClient) -> None:
    _set_session(client, {"user_id": "u1"})
    r = client.post(
        "/api/jobs/parse",
        json={"source_type": "manual", "position_title": "only"},
    )
    assert r.status_code == 400


def test_jobs_parse_url_crawl_failed(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fail_fetch(_url: str) -> tuple[str, str]:
        raise httpx.HTTPError("network")

    monkeypatch.setattr("src.api.jobs._fetch_url_text", fail_fetch)
    _set_session(client, {"user_id": "u1"})
    r = client.post(
        "/api/jobs/parse",
        json={"source_type": "url", "url": "https://example.com/job"},
    )
    assert r.status_code == 400
    assert r.json().get("error") == "CRAWL_FAILED"
