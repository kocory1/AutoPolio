"""
OpenAI Chat Completions 기반 개발자 관점 코드/폴더/프로젝트 요약.
"""

from __future__ import annotations

import os

from openai import AsyncOpenAI

from src.service.github_embedding.prompts import (
    DEVELOPER_FILE_SUMMARY_SYSTEM,
    DEVELOPER_FOLDER_SUMMARY_SYSTEM,
    DEVELOPER_PROJECT_SUMMARY_SYSTEM,
)

DEFAULT_CHAT_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
# 단일 요청 토큰 상한 완화용(비용·지연과 트레이드오프)
MAX_SOURCE_CHARS = int(os.getenv("GITHUB_EMBED_MAX_SOURCE_CHARS", "120000"))


def _truncate_source(source_code: str) -> tuple[str, bool]:
    if len(source_code) <= MAX_SOURCE_CHARS:
        return source_code, False
    return source_code[:MAX_SOURCE_CHARS], True


class OpenAIDeveloperSummarizer:
    """파이프라인용: 파일·폴더·프로젝트 요약을 한국어 개발자 관점으로 생성."""

    def __init__(
        self,
        *,
        model: str | None = None,
        api_key: str | None = None,
        temperature: float = 0.25,
    ) -> None:
        key = api_key or os.getenv("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        self._client = AsyncOpenAI(api_key=key)
        self._model = model or DEFAULT_CHAT_MODEL
        self._temperature = temperature

    async def _complete(self, system: str, user: str) -> str:
        resp = await self._client.chat.completions.create(
            model=self._model,
            temperature=self._temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        choice = resp.choices[0].message.content
        return (choice or "").strip()

    async def summarize_file(
        self,
        repo_full_name: str,
        path: str,
        source_code: str,
    ) -> str:
        body, truncated = _truncate_source(source_code)
        note = ""
        if truncated:
            note = f"\n\n(원문 {len(source_code)}자 중 앞 {MAX_SOURCE_CHARS}자만 전달됨.)"
        user = (
            f"레포지토리: `{repo_full_name}`\n"
            f"파일 경로: `{path}`\n{note}\n\n"
            f"--- 소스 코드 시작 ---\n{body}\n--- 소스 코드 끝 ---"
        )
        return await self._complete(DEVELOPER_FILE_SUMMARY_SYSTEM, user)

    async def summarize_folder(
        self,
        repo_full_name: str,
        folder_path: str,
        child_summaries: list[str],
    ) -> str:
        blocks = "\n\n---\n\n".join(
            f"[{i + 1}]\n{s}" for i, s in enumerate(child_summaries)
        )
        user = (
            f"레포지토리: `{repo_full_name}`\n"
            f"디렉터리 경로: `{folder_path or '(루트)'}`\n\n"
            f"하위 요약들:\n\n{blocks}"
        )
        return await self._complete(DEVELOPER_FOLDER_SUMMARY_SYSTEM, user)

    async def summarize_project(
        self,
        repo_full_name: str,
        root_child_summaries: list[str],
    ) -> str:
        blocks = "\n\n---\n\n".join(
            f"[{i + 1}]\n{s}" for i, s in enumerate(root_child_summaries)
        )
        user = (
            f"레포지토리: `{repo_full_name}`\n\n"
            f"루트 직계 요약들:\n\n{blocks}"
        )
        return await self._complete(DEVELOPER_PROJECT_SUMMARY_SYSTEM, user)
