#!/usr/bin/env python3
"""
합격 자소서 본문 텍스트에서 LLM으로 문항(question) / 답변(answer) 추출.
OpenAI API 사용. 환경변수 OPENAI_API_KEY 필요.

사용 예:
  from llm_cover_letter import extract_questions_answers
  result = extract_questions_answers(body_text, source="링커리어")
"""

import json
import os
import re
from typing import Any, List, Optional

EXTRACT_SYSTEM = """당신은 합격 자기소개서 본문을 분석하는 도우미입니다.
주어진 텍스트는 자소서 본문만 있습니다. 문단/번호/대괄호 등 형식에 상관없이, 각 "문항(질문)"과 그에 대한 "답변(지원자가 쓴 내용)"을 구분해 추출하세요.
- 문항: 채용처가 낸 질문 또는 항목 제목 (예: "지원동기를 기술하시오", "1. 성격의 장단점", "[직무] 지원 분야를 위해...")
- 답변: 해당 문항에 대해 지원자가 작성한 본문. 글자수 안내·괄호는 제외하고 실제 에세이만 넣으세요.
- 본문이 아닌 UI 텍스트(목록보기, 스크랩, 로그인 유도 등)는 제외하세요.
반드시 아래 JSON 형태로만 답하고, 다른 설명은 붙이지 마세요."""

EXTRACT_USER_TEMPLATE = """다음 자소서 본문에서 문항(question)과 답변(answer) 쌍을 추출해 JSON 배열로 주세요.
출력 형식만 다음처럼 하고, 설명 없이 JSON만 출력하세요:
{"questions": [{"question": "첫 번째 문항 텍스트", "answer": "첫 번째 답변 전문"}, ...]}

본문:
---
{text}
---"""


def extract_questions_answers(
    body_text: str,
    source: str = "링커리어",
    model: str = "gpt-4o-mini",
    max_tokens: int = 4096,
) -> Optional[List[dict]]:
    """
    자소서 본문 텍스트에서 문항/답변 리스트 추출.
    반환: [{"question": str, "answer": str}, ...] 또는 실패 시 None
    """
    if not body_text or len(body_text.strip()) < 50:
        return []
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY 환경변수를 설정하세요.")
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("openai 패키지 필요: poetry add openai")

    client = OpenAI(api_key=api_key)
    # 토큰 제한 고려해 본문 자르기 (대략 12k자 = 수천 토큰)
    text = body_text.strip()[:12000]
    user_content = EXTRACT_USER_TEMPLATE.format(text=text)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": EXTRACT_SYSTEM},
            {"role": "user", "content": user_content},
        ],
        max_tokens=max_tokens,
        temperature=0,
    )
    content = (resp.choices[0].message.content or "").strip()
    if not content:
        return None
    # JSON 블록만 추출 (마크다운 코드블록 제거)
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", content)
    if json_match:
        content = json_match.group(1).strip()
    # { "questions": [ ... ] } 또는 [ ... ] 형태 허용
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return None
    if isinstance(data, list):
        questions = data
    elif isinstance(data, dict) and "questions" in data:
        questions = data["questions"]
    else:
        return None
    if not isinstance(questions, list):
        return None
    result: List[dict] = []
    for item in questions:
        if not isinstance(item, dict):
            continue
        q = item.get("question") or item.get("q") or ""
        a = item.get("answer") or item.get("a") or ""
        if isinstance(q, str) and isinstance(a, str):
            result.append({"question": q[:800], "answer": a[:15000]})
    return result if result else None
