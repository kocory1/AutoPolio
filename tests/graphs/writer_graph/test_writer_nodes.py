"""writer_graph.node 단위 테스트 (구현 전 TDD — 노드가 async·의존성 연동 시 통과).

구현 시 권장:
- ``from src.service.rag import retrieve_passed_cover_letters, retrieve_user_assets`` 처럼
  모듈 전역 이름으로 import 후 호출하면, 본 테스트의 ``monkeypatch.setattr(writer_node, ...)`` 가
  런타임에 해당 이름을 교체한다.
- ``langchain_openai.ChatOpenAI`` 도 ``writer_graph.node`` 모듈에서 import 해 두고
  ``writer_node.ChatOpenAI`` 로 패치 가능하게 한다.
"""

from __future__ import annotations

import inspect
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import HumanMessage

from src.graphs.writer_graph import node as writer_node


async def _call_node(fn, *args, **kwargs):
    out = fn(*args, **kwargs)
    if inspect.isawaitable(out):
        return await out
    return out


# ---------------------------------------------------------------------------
# retrieve_samples
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retrieve_samples_missing_question(monkeypatch):
    monkeypatch.setattr(
        writer_node,
        "retrieve_passed_cover_letters",
        AsyncMock(side_effect=AssertionError("should not call retrieve")),
        raising=False,
    )

    state = {"max_chars": 500}
    result = await _call_node(writer_node.retrieve_samples, state)

    assert result.get("error"), "question 누락 시 error가 설정되어야 함"
    assert "question" in str(result["error"]).lower()
    assert "samples" not in result or result.get("samples") in (None, [])


@pytest.mark.asyncio
async def test_retrieve_samples_missing_max_chars(monkeypatch):
    monkeypatch.setattr(
        writer_node,
        "retrieve_passed_cover_letters",
        AsyncMock(side_effect=AssertionError("should not call retrieve")),
        raising=False,
    )

    state = {"question": "지원 동기를 서술하세요."}
    result = await _call_node(writer_node.retrieve_samples, state)

    assert result.get("error"), "max_chars 누락 시 error가 설정되어야 함"
    assert "max_chars" in str(result["error"]).lower()


@pytest.mark.asyncio
async def test_retrieve_samples_success_with_results(monkeypatch):
    samples_out = [
        {
            "question": "Q1",
            "answer": "A1",
            "company": "ACME",
            "position": "백엔드",
            "year": "2024",
            "source": "잡코리아",
            "distance": 0.1,
        }
    ]

    mock_retrieve = AsyncMock(return_value=samples_out)
    monkeypatch.setattr(
        writer_node,
        "retrieve_passed_cover_letters",
        mock_retrieve,
        raising=False,
    )

    state = {
        "question": "성장 과정을 서술하세요.",
        "max_chars": 800,
        "job_parsed": {"company_name": "ACME", "position": "백엔드", "year": "2024"},
    }
    result = await _call_node(writer_node.retrieve_samples, state)

    assert result.get("error") in (None, ""), "성공 시 error 없음"
    assert result.get("samples") == samples_out
    mock_retrieve.assert_awaited_once()


@pytest.mark.asyncio
async def test_retrieve_samples_empty_result_no_error(monkeypatch):
    mock_retrieve = AsyncMock(return_value=[])
    monkeypatch.setattr(
        writer_node,
        "retrieve_passed_cover_letters",
        mock_retrieve,
        raising=False,
    )

    state = {
        "question": "문항",
        "max_chars": 300,
        "job_parsed": {},
    }
    result = await _call_node(writer_node.retrieve_samples, state)

    assert not result.get("error"), "빈 검색이어도 error 없이 통과"
    assert result.get("samples") == []
    mock_retrieve.assert_awaited_once()


# ---------------------------------------------------------------------------
# load_assets
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_load_assets_missing_user_id(monkeypatch):
    monkeypatch.setattr(
        writer_node,
        "retrieve_user_assets",
        AsyncMock(side_effect=AssertionError("should not call retrieve_user_assets")),
        raising=False,
    )

    state = {"question": "Q", "max_chars": 100}
    result = await _call_node(writer_node.load_assets, state)

    assert result.get("error"), "user_id 없으면 error"
    assert "user_id" in str(result["error"]).lower()


@pytest.mark.asyncio
async def test_load_assets_empty_result_sets_error(monkeypatch):
    monkeypatch.setattr(
        writer_node,
        "retrieve_user_assets",
        AsyncMock(return_value=[]),
        raising=False,
    )

    state = {
        "user_id": "u1",
        "question": "Q",
        "max_chars": 100,
        "job_parsed": {},
    }
    result = await _call_node(writer_node.load_assets, state)

    assert result.get("error"), "에셋이 비면 error"
    assert "assets" not in result or result.get("assets") == []


@pytest.mark.asyncio
async def test_load_assets_success(monkeypatch):
    assets_out = [
        {"id": "a1", "document": "요약1", "metadata": {"type": "code"}},
    ]
    monkeypatch.setattr(
        writer_node,
        "retrieve_user_assets",
        AsyncMock(return_value=assets_out),
        raising=False,
    )

    state = {
        "user_id": "u1",
        "question": "Q",
        "max_chars": 500,
        "job_parsed": {"company_name": "ACME"},
    }
    result = await _call_node(writer_node.load_assets, state)

    assert not result.get("error")
    assert result.get("assets") == assets_out


# ---------------------------------------------------------------------------
# generate_draft
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_draft_basic(monkeypatch):
    class FakeAIMessage:
        content = json.dumps({"draft": "테스트 초안"}, ensure_ascii=False)

    instance = MagicMock()
    instance.ainvoke = AsyncMock(return_value=FakeAIMessage())
    monkeypatch.setattr(
        writer_node,
        "ChatOpenAI",
        MagicMock(return_value=instance),
        raising=False,
    )

    state = {
        "question": "문항",
        "max_chars": 500,
        "job_parsed": {"company_name": "ACME"},
        "assets": [{"id": "x", "document": "evidence"}],
        "samples": [{"question": "s1", "answer": "a1"}],
    }
    result = await _call_node(writer_node.generate_draft, state)

    assert result.get("draft") == "테스트 초안"
    instance.ainvoke.assert_awaited()


@pytest.mark.asyncio
async def test_generate_draft_with_consistency_feedback(monkeypatch):
    marker = "UNIQUE_CONSISTENCY_FEEDBACK_MARKER"

    class FakeAIMessage:
        content = json.dumps({"draft": "수정 초안"}, ensure_ascii=False)

    captured_messages = []

    async def capture_ainvoke(messages):
        captured_messages.append(messages)
        return FakeAIMessage()

    instance = MagicMock()
    instance.ainvoke = AsyncMock(side_effect=capture_ainvoke)
    monkeypatch.setattr(
        writer_node,
        "ChatOpenAI",
        MagicMock(return_value=instance),
        raising=False,
    )

    state = {
        "question": "문항",
        "max_chars": 500,
        "job_parsed": {},
        "assets": [{"id": "1", "document": "d"}],
        "samples": [],
        "consistency_feedback": {
            "issues": [{"sentence": "가짜 문장", "reason": marker}],
        },
    }
    await _call_node(writer_node.generate_draft, state)

    assert captured_messages, "LLM 호출되어야 함"
    flat = captured_messages[0]
    human_parts = [m.content for m in flat if isinstance(m, HumanMessage)]
    assert human_parts, "HumanMessage가 있어야 함"
    joined = "\n".join(
        c if isinstance(c, str) else json.dumps(c, ensure_ascii=False) for c in human_parts
    )
    assert marker in joined, "user 쪽 메시지에 consistency_feedback 내용이 포함되어야 함"


# ---------------------------------------------------------------------------
# self_consistency
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_self_consistency_pass(monkeypatch):
    class FakeAIMessage:
        content = json.dumps(
            {
                "is_hallucination": False,
                "consistency_feedback": {"issues": []},
            },
            ensure_ascii=False,
        )

    instance = MagicMock()
    instance.ainvoke = AsyncMock(return_value=FakeAIMessage())
    monkeypatch.setattr(
        writer_node,
        "ChatOpenAI",
        MagicMock(return_value=instance),
        raising=False,
    )

    state = {
        "draft": "초안",
        "assets": [{"document": "근거"}],
        "draft_retry_count": 2,
    }
    result = await _call_node(writer_node.self_consistency, state)

    assert result.get("is_hallucination") is False
    assert result.get("draft_retry_count") == 2


@pytest.mark.asyncio
async def test_self_consistency_fail(monkeypatch):
    feedback = {"issues": [{"sentence": "문제 문장", "reason": "assets에 없음"}]}

    class FakeAIMessage:
        content = json.dumps(
            {"is_hallucination": True, "consistency_feedback": feedback},
            ensure_ascii=False,
        )

    instance = MagicMock()
    instance.ainvoke = AsyncMock(return_value=FakeAIMessage())
    monkeypatch.setattr(
        writer_node,
        "ChatOpenAI",
        MagicMock(return_value=instance),
        raising=False,
    )

    state = {
        "draft": "과장된 초안",
        "assets": [],
        "draft_retry_count": 0,
    }
    result = await _call_node(writer_node.self_consistency, state)

    assert result.get("is_hallucination") is True
    assert result.get("draft_retry_count") == 1
    assert result.get("consistency_feedback") == feedback


# ---------------------------------------------------------------------------
# format_output
# ---------------------------------------------------------------------------


def test_format_output_truncates_to_max_chars():
    long_draft = "가" * 100
    state = {"draft": long_draft, "max_chars": 10}
    result = writer_node.format_output(state)

    assert len(result["draft"]) == 10
    assert result["draft"] == "가" * 10


def test_format_output_no_max_chars():
    text = "본문\n그대로"
    state = {"draft": text}
    result = writer_node.format_output(state)

    assert result["draft"] == text


def test_format_output_cleans_whitespace():
    state = {
        "draft": "첫줄\n\n\n\n둘째",
        "max_chars": 10_000,
    }
    result = writer_node.format_output(state)

    # 연속 줄바꿈은 단일 줄바꿈으로 정리 (구현 기대값)
    assert result["draft"] == "첫줄\n둘째"
