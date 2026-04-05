"""Inspector analyze 노드용 프롬프트."""

INSPECTOR_SYSTEM_PROMPT = """You are an expert cover-letter editor for Korean tech job applications.
Given the user's draft, retrieved portfolio evidence snippets, and (if any) sample cover letters,
produce actionable improvement suggestions in JSON.

Respond with a single JSON object only, with this shape:
{"suggestions": [
  {
    "section": "short label for which part of the letter (e.g. opening, motivation, experience)",
    "suggestion": "concrete rewrite or fix in Korean",
    "rationale": "why this helps, citing evidence or best practice briefly",
    "priority": "high" | "medium" | "low"
  }
]}
Use Korean for section, suggestion, and rationale. Order suggestions by priority (high first).
If the draft is already strong, return fewer items with priority low or medium.
"""


def build_inspector_user_prompt(
    *,
    draft: str,
    question: str,
    assets_brief: list[dict],
    samples_brief: list[dict],
    round_num: int,
) -> str:
    """analyze용 유저 메시지 본문."""
    lines: list[str] = [
        "## 문항/맥락",
        question or "(없음)",
        "",
        "## 초안",
        draft,
        "",
        "## 포트폴리오 근거 스니펫 (요약)",
    ]
    if not assets_brief:
        lines.append("(조회 결과 없음)")
    else:
        for i, item in enumerate(assets_brief, start=1):
            lines.append(f"{i}. {item.get('summary', '')}")

    lines.extend(["", "## 합격 자소서 예시 (참고, 일부)"])
    if not samples_brief:
        lines.append("(현재 예시 없음)")
    else:
        for i, item in enumerate(samples_brief, start=1):
            lines.append(f"{i}. {item.get('summary', '')}")

    if round_num > 0:
        lines.extend(
            [
                "",
                "## 재첨삭 안내",
                "이전 라운드 피드백을 반영해 사용자가 수정한 초안입니다. "
                "남은 문제·새로운 리스크·놓친 근거를 중심으로 제안하세요.",
            ]
        )

    return "\n".join(lines)
