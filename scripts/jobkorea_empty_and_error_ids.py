#!/usr/bin/env python3
"""
1. 빈 답변: 해당 문항이 면접 문항인지 체크
2. 에러/로딩 메시지가 포함된 답변이 있는 파일 id 리스트 출력

사용: poetry run python scripts/jobkorea_empty_and_error_ids.py
"""

import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
JOBKOREA_DIR = PROJECT_ROOT / "data" / "jobkorea"

# 에러/로딩 메시지 (사이트 전용 안내 문구만. 자소서에 자주 나오는 "오류가 발생했습니다" 등은 제외)
ERROR_PATTERNS = [
    r"답변을\s*불러올\s*수\s*없",
    r"로딩\s*중입니다",
    r"잠시\s*후\s*다시\s*시도",
]
ERROR_RE = re.compile("|".join(f"({p})" for p in ERROR_PATTERNS), re.IGNORECASE)

# 면접 문항으로 보는 문항 패턴 (서면 자소서가 아닌 구두/면접 질문 느낌)
INTERVIEW_QUESTION_PATTERNS = [
    r"\d+\s*분\s*자기소개",           # N분 자기소개
    r"\d+\s*분\s*자기\s*소개",
    r"자기소개\s*해\s*보세요",
    r"자기소개\s*해보세요",
    r"자기소개\s*해\s*주세요",
    r"자기소개를\s*해보세요",
    r"자기소개를\s*해\s*보세요",
    r"PT\s*발표",
    r"토론하라\s*$",
    r"토론하시오\s*$",
    r"면접\s*$",
    r"^\s*면접\s*$",
]
INTERVIEW_RE = re.compile("|".join(f"({p})" for p in INTERVIEW_QUESTION_PATTERNS), re.IGNORECASE)


def is_interview_question(question: str) -> bool:
    """문항 텍스트가 면접(구두) 문항으로 보이면 True."""
    if not question or not isinstance(question, str):
        return False
    return bool(INTERVIEW_RE.search(question.strip()))


def has_error_message(answer: str) -> bool:
    if answer is None or not isinstance(answer, str):
        return False
    return bool(ERROR_RE.search(answer))


def main() -> None:
    if not JOBKOREA_DIR.is_dir():
        print(f"Not a directory: {JOBKOREA_DIR}")
        return

    files = sorted(JOBKOREA_DIR.glob("*.json"))
    empty_entries = []   # (id, q_idx, question, is_interview)
    error_ids = set()    # id

    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        file_id = path.stem
        questions = data.get("questions") or []
        for q_idx, q in enumerate(questions):
            question = q.get("question") or ""
            answer = q.get("answer")
            text = (answer or "").strip()
            # 빈 답변
            if len(text) == 0:
                is_interview = is_interview_question(question)
                empty_entries.append((file_id, q_idx, question.strip()[:80], is_interview))
            # 에러 메시지 포함
            if has_error_message(answer):
                error_ids.add(file_id)

    # --- 빈 답변 + 면접 문항 여부 ---
    print("=" * 80)
    print("빈 답변 문항 (면접 문항 여부)")
    print("=" * 80)
    interview_count = sum(1 for _ in empty_entries if _[3])
    non_interview_count = len(empty_entries) - interview_count
    print(f"총 빈 답변: {len(empty_entries)}개  (면접 문항: {interview_count}개, 비면접: {non_interview_count}개)\n")
    for file_id, q_idx, q_preview, is_interview in empty_entries:
        tag = " [면접 문항]" if is_interview else " [비면접]"
        print(f"  {file_id}  q_idx={q_idx}{tag}")
        print(f"    문항: {q_preview}")
    print()

    # --- 에러 메시지 포함 id 리스트 ---
    print("=" * 80)
    print("에러/로딩 메시지가 포함된 답변이 있는 파일 ID 목록")
    print("=" * 80)
    print(f"총 {len(error_ids)}개\n")
    for id_ in sorted(error_ids, key=lambda x: int(x) if x.isdigit() else 0):
        print(id_)
    print()
    # 한 줄로도 출력 (복사용)
    print("ID 리스트 (쉼표 구분):")
    print(",".join(sorted(error_ids, key=lambda x: int(x) if x.isdigit() else 0)))


if __name__ == "__main__":
    main()
