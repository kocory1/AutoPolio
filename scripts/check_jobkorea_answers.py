#!/usr/bin/env python3
"""
jobkorea 폴더 내 모든 JSON의 answer 필드를 검사하여
자기소개서 답변 외의 불필요한 내용(UI 텍스트, 크롤링 잔여물 등)이 있는지 확인.

검사 항목:
1. clean_jobkorea_answers.py에서 제거 대상으로 정의한 마커가 아직 남아있는지
2. HTML 태그
3. 에러/로딩 메시지 (답변을 불러올 수 없습니다 등)
4. 빈 답변 또는 극단적으로 짧은 답변
5. 문항(question) 텍스트가 답변 앞부분에 그대로 포함된 경우
"""

import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
JOBKOREA_DIR = PROJECT_ROOT / "data" / "jobkorea"

# 자소서 본문이 아닌 UI/사이드바 마커 (clean_jobkorea_answers.py와 동일)
JUNK_MARKERS = [
    (r"글자수\s*\d[\d,\s\n]*자\s*\d[\d,\s\n]*Byte?", "글자수 N자 N Byte"),
    (r"\n\s*목록보기|\s+목록보기(?!\w)", "목록보기"),
    (r"\n\s*전체보기", "전체보기"),
    (r"\n\s*1초\s*로그인", "1초 로그인"),
    (r"\n\s*인적성\s*·\s*면접후기|인적성후기\s*\d+\s*개\s*더보기", "인적성·면접후기"),
    (r"\n\s*직무인터뷰", "직무인터뷰"),
    (r"\n\s*면접질문\s*\n", "면접질문"),
    (r"\n\s*진행중인\s*채용공고", "진행중인 채용공고"),
    (r"\n\s*다른\s*취업정보", "다른 취업정보"),
    (r"\n\s*로그인\s*레이어\s*닫기", "로그인 레이어 닫기"),
    (r"\n\s*'\s*[^']+\s*'\s*의\s*인기\s*합격자소서", "인기 합격자소서"),
    (r"\n\s*'\s*[^']+\s*'\s*인적성", "회사명 인적성"),
    (r"\n\s*면접\s*$", "끝의 '면접' 버튼"),
    (r"\n\s*D-\d+\s*\n", "D-N 채용공고 스니펫"),
]

# 에러/로딩 메시지 (사이트 전용 안내만. 자소서에 자주 나오는 "오류가 발생했습니다" 등 제외)
ERROR_PATTERNS = [
    (r"답변을\s*불러올\s*수\s*없", "답변 불러오기 실패 메시지"),
    (r"로딩\s*중입니다", "로딩 메시지"),
    (r"잠시\s*후\s*다시\s*시도", "재시도 안내"),
]

# HTML 태그
HTML_TAG_RE = re.compile(r"<[^>]+>", re.IGNORECASE)

# 답변이 문항과 동일/거의 동일한 경우 감지 (앞 100자 기준)
def answer_starts_with_question(question: str, answer: str) -> bool:
    if not question or not answer or len(answer) < 50:
        return False
    q_clean = question.strip()[:80]
    a_clean = answer.strip()[:80]
    if not q_clean or not a_clean:
        return False
    # 문항이 답변 앞에 그대로 포함된 경우 (공백/줄바꿈 정규화)
    q_norm = re.sub(r"\s+", " ", q_clean)
    a_norm = re.sub(r"\s+", " ", a_clean)
    return q_norm in a_norm or a_norm.startswith(q_norm[:50])


def check_answer(file_id: str, q_idx: int, question: str, answer: str) -> list[tuple[str, str]]:
    """단일 answer 검사. (이슈 유형, 스니펫) 리스트 반환."""
    issues = []
    if answer is None:
        issues.append(("빈 값", "answer가 null"))
        return issues
    if not isinstance(answer, str):
        issues.append(("타입 오류", f"answer가 str이 아님: {type(answer)}"))
        return issues
    text = answer.strip()
    if len(text) == 0:
        issues.append(("빈 답변", "(내용 없음)"))
        return issues
    if len(text) < 30:
        issues.append(("매우 짧은 답변", f"길이 {len(text)}자: {text[:50]}..."))

    for pat, name in JUNK_MARKERS:
        if re.search(pat, answer, re.IGNORECASE):
            m = re.search(pat, answer, re.IGNORECASE)
            snippet = (answer[m.start() : m.end() + 30] if m else "")[:60]
            issues.append((f"UI/잔여물: {name}", snippet))

    for pat, name in ERROR_PATTERNS:
        if re.search(pat, answer, re.IGNORECASE):
            issues.append((f"에러/로딩: {name}", ""))

    if HTML_TAG_RE.search(answer):
        tags = HTML_TAG_RE.findall(answer)
        issues.append(("HTML 태그 포함", ", ".join(tags[:5])))

    if answer_starts_with_question(question, answer):
        issues.append(("문항이 답변 앞에 포함", answer[:80] + "..."))

    return issues


def main() -> None:
    if not JOBKOREA_DIR.is_dir():
        print(f"Not a directory: {JOBKOREA_DIR}")
        return
    files = sorted(JOBKOREA_DIR.glob("*.json"))
    total_answers = 0
    files_with_issues = 0
    all_issues = []  # (file_id, q_idx, question_preview, issues)

    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            all_issues.append((path.stem, -1, "", [("파일 오류", str(e))]))
            files_with_issues += 1
            continue

        questions = data.get("questions") or []
        file_has_issue = False
        for q_idx, q in enumerate(questions):
            total_answers += 1
            question = q.get("question") or ""
            answer = q.get("answer")
            issues = check_answer(path.stem, q_idx, question, answer)
            if issues:
                file_has_issue = True
                all_issues.append((path.stem, q_idx, question[:60] + ("..." if len(question) > 60 else ""), issues))
        if file_has_issue:
            files_with_issues += 1

    # 리포트 출력
    print("=" * 80)
    print("jobkorea answer 검사 결과: 자기소개서 답변 외 불필요한 내용 여부")
    print("=" * 80)
    print(f"총 파일 수: {len(files)}, 총 답변 수: {total_answers}")
    print(f"이슈 있는 항목 수: {len(all_issues)}, 이슈 있는 파일 수: {files_with_issues}")
    print()

    # 이슈 유형별 집계
    type_count = {}
    for _fid, _qi, _q, issue_list in all_issues:
        for typ, _ in issue_list:
            type_count[typ] = type_count.get(typ, 0) + 1
    print("--- 이슈 유형별 건수 ---")
    for typ, cnt in sorted(type_count.items(), key=lambda x: -x[1]):
        print(f"  {cnt:4d}  {typ}")
    print()

    print("--- 파일별·문항별 상세 (이슈 있는 것만) ---")
    for file_id, q_idx, q_preview, issues in all_issues:
        print(f"\n[{file_id}] 문항 index={q_idx}")
        if q_preview:
            print(f"  문항: {q_preview}")
        for typ, snippet in issues:
            if snippet:
                print(f"  - {typ}: {snippet[:70]}")
            else:
                print(f"  - {typ}")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
