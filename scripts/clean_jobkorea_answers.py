#!/usr/bin/env python3
"""
jobkorea 폴더 내 모든 JSON의 answer 필드에서 자소서 본문이 아닌 내용 제거.

제거 대상:
- 글자수 N자 N Byte
- 목록보기 / 전체보기 이후 사이드바·링크 (인기 합격자소서, 읽음 수 등)
- 1초 로그인으로 ... 로그인 레이어 닫기
- 인적성·면접후기 / 인적성후기 N개 더보기 / 면접질문 / 직무인터뷰
- 진행중인 채용공고, D-N 스니펫
- 끝의 단독 "면접" 버튼 텍스트

사용: poetry run python scripts/clean_jobkorea_answers.py
"""

import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
JOBKOREA_DIR = PROJECT_ROOT / "data" / "jobkorea"


def clean_answer(text: str) -> str:
    if not text or not isinstance(text, str):
        return text
    s = text

    # 1) 글자수 N자 N Byte 제거 (줄바꿈/쉼표 포함 다양한 형식)
    s = re.sub(
        r"\s*글자수\s*\d[\d,\s\n]*자\s*\d[\d,\s\n]*Byte?\s*",
        " ",
        s,
        flags=re.IGNORECASE,
    )

    # 2) 자소서 본문 이후 나오는 UI/사이드바 구간 잘라내기 (가장 먼저 나오는 마커 기준)
    junk_markers = [
        r"\n\s*목록보기",
        r"\s+목록보기(?!\w)",  # 문장 끝 ". 목록보기" 등
        r"\n\s*전체보기",
        r"\n\s*1초\s*로그인",
        r"\n\s*인적성\s*·\s*면접후기",
        r"\n\s*인적성후기\s*\d+\s*개\s*더보기",
        r"\n\s*직무인터뷰",
        r"\n\s*면접질문\s*\n",
        r"\n\s*진행중인\s*채용공고",
        r"\n\s*다른\s*취업정보",
        r"\n\s*로그인\s*레이어\s*닫기",
        # '회사명' 의 인기 합격자소서 (따옴표로 시작하는 줄)
        r"\n\s*'\s*[^']+\s*'\s*의\s*인기\s*합격자소서",
        r"\n\s*'\s*[^']+\s*'\s*인적성",
    ]
    earliest = len(s)
    for pat in junk_markers:
        m = re.search(pat, s, re.IGNORECASE)
        if m:
            earliest = min(earliest, m.start())
    if earliest < len(s):
        s = s[:earliest]

    # 3) 끝의 단독 "면접" (버튼/링크 텍스트) 제거
    s = re.sub(r"\n\s*면접\s*$", "", s)

    # 4) 끝의 "D-\d+" 채용공고 스니펫 제거 (예: D-3\n\n서비스지원직군...)
    s = re.sub(r"\n\s*D-\d+\s*\n.*$", "", s, flags=re.DOTALL)

    # 5) 앞뒤 공백·과도한 줄바꿈 정리 (연속 줄바꿈은 최대 2개로)
    s = re.sub(r"\n{3,}", "\n\n", s)
    s = s.strip()
    return s


def process_file(path: Path) -> bool:
    """JSON 파일을 읽어 questions[].answer 를 정리한 뒤 저장. 변경 여부 반환."""
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  skip {path.name}: {e}")
        return False

    questions = data.get("questions")
    if not questions:
        return False

    changed = False
    for q in questions:
        if "answer" not in q:
            continue
        orig = q["answer"]
        cleaned = clean_answer(orig)
        if cleaned != orig:
            q["answer"] = cleaned
            changed = True

    if changed:
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    return changed


def main() -> None:
    if not JOBKOREA_DIR.is_dir():
        print(f"Not a directory: {JOBKOREA_DIR}")
        return
    files = sorted(JOBKOREA_DIR.glob("*.json"))
    updated = 0
    for p in files:
        if process_file(p):
            updated += 1
    print(f"Done. Updated {updated} / {len(files)} files.")


if __name__ == "__main__":
    main()
