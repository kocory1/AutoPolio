#!/usr/bin/env python3
"""
잡코리아 합격 자소서 상세 수집 스크립트 (2단계)

- data/jobkorea_urls.json 의 URL 목록을 읽어서
- 각 상세 페이지를 요청 → 회사명, 직무·연도, 문항+답변, 전문가 피드백 파싱
- data/jobkorea/{id}.json 으로 저장 (이미 있으면 스킵, 재실행 시 이어하기)

사용: poetry run python scripts/jobkorea_crawl_detail.py
"""

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional

import requests
from bs4 import BeautifulSoup

# --- 경로 ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
URLS_PATH = PROJECT_ROOT / "data" / "jobkorea_urls.json"
OUTPUT_DIR = PROJECT_ROOT / "data" / "jobkorea"
REQUEST_DELAY_SEC = 1.5
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}


def load_url_list() -> List[dict]:
    with open(URLS_PATH, encoding="utf-8") as f:
        return json.load(f)


def fetch_html(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.text


def parse_year_from_position_text(text: str) -> tuple[str, str]:
    """'2018년 하반기 신입 앱개발자' -> ('2018년 하반기', '신입 앱개발자')"""
    text = (text or "").strip()
    m = re.match(r"^(\d{4}년\s*(?:상|하)반기)\s*(.*)$", text)
    if m:
        return m.group(1).strip(), m.group(2).strip() or text
    return "", text


def parse_detail_page(html: str, doc_id: str, url: str) -> Optional[Any]:
    soup = BeautifulSoup(html, "html.parser")

    # 회사명: 제목 영역 strong
    company = ""
    title_strong = soup.select_one("h2 strong, .tit strong, .passassay-head strong")
    if title_strong:
        company = title_strong.get_text(strip=True).replace("관심기업", "").strip()

    # 직무·연도: 제목 영역 em
    position_full = ""
    title_em = soup.select_one("h2 em, .tit em, .passassay-head em")
    if title_em:
        position_full = title_em.get_text(strip=True)
    year, position = parse_year_from_position_text(position_full)
    if not position and position_full:
        position = position_full

    # 문항 + 답변: 본문 텍스트에서 "질문" / "답변" 구간으로 추출 (잡코리아는 클래스명이 페이지마다 다를 수 있음)
    questions = []
    # 가능한 본문 영역 순서대로 시도
    body = (
        soup.select_one(".passassay-detail, .viewContent, .selfIntro, .detailContent")
        or soup.select_one("#content, main, article, .content, .container, #wrap")
        or soup.body
    )
    def _append_qa(q_text: str, a_text: str) -> None:
        q_text = re.sub(r"^Q?\d+\.?\s*", "", q_text.strip())
        q_text = re.sub(r"\s*보기\s*$", "", q_text, flags=re.IGNORECASE)
        a_text = re.sub(r"\n?\s*글자수\s*\d+자\s*\d+Byte?\s*$", "", a_text.strip(), flags=re.IGNORECASE)
        a_text = re.sub(r"\n?\s*아쉬운점\s*\d+.*$", "", a_text, flags=re.DOTALL)
        a_text = re.sub(r"\n?\s*좋은점\s*\d+.*$", "", a_text, flags=re.DOTALL)
        # 면접후기/더보기 등 잡블록 제외: 질문이 너무 길거나 특정 키워드 포함 시 스킵
        if re.search(r"더보기|면접후기|로그인", q_text):
            return
        if len(q_text) > 600 and not a_text.strip():
            return
        if q_text or a_text:
            questions.append({"question": q_text[:800], "answer": a_text[:15000]})

    if body:
        text = body.get_text(separator="\n")
        # 1) "질문 Q1." / "질문 1." / "질문" 형태로 블록 나누기 ("질문 및 내용" 같은 문구에서 잘리지 않도록 질문+번호 우선)
        parts = re.split(r"\s*질문\s+(?:Q?\d+\.?)\s*", text, flags=re.IGNORECASE)
        if len(parts) <= 1:
            parts = re.split(r"\s*질문\s*", text, flags=re.IGNORECASE)
        if len(parts) > 1:
            for i, part in enumerate(parts):
                if i == 0:
                    continue
                part = part.strip()
                q_and_a = re.split(r"\s*답변\s*보기\s*|\s*답변\s*", part, maxsplit=1, flags=re.IGNORECASE)
                q_text = (q_and_a[0].strip() if q_and_a else "").strip()
                a_text = (q_and_a[1].strip() if len(q_and_a) > 1 else "").strip()
                _append_qa(q_text, a_text)
        else:
            # 2) "질문" 없으면 Q1. Q2. Q3. ... 로 블록 나누기
            parts = re.split(r"\s*(?=Q\d+\.)", text)
            for part in parts:
                part = part.strip()
                if not part or not re.match(r"^Q\d+\.", part):
                    continue
                q_and_a = re.split(r"\s*답변\s*보기\s*|\s*답변\s*", part, maxsplit=1, flags=re.IGNORECASE)
                q_text = (q_and_a[0].strip() if q_and_a else "").strip()
                a_text = (q_and_a[1].strip() if len(q_and_a) > 1 else "").strip()
                _append_qa(q_text, a_text)

    # 전문가 총평
    expert_feedback = None
    expert_section = soup.select_one(".expertReview, .expert-review, [class*='expert'], [class*='총평']")
    if expert_section:
        summary_el = expert_section.select_one("p, .summary, .txt")
        summary = summary_el.get_text(strip=True)[:2000] if summary_el else ""
        good_el = expert_section.select(".good, .good_point, [class*='좋은']")
        weak_el = expert_section.select(".weak, .weak_point, [class*='아쉬운']")
        good_points = [e.get_text(strip=True) for e in good_el][:20]
        weak_points = [e.get_text(strip=True) for e in weak_el][:20]
        if summary or good_points or weak_points:
            expert_feedback = {
                "summary": summary,
                "good_points": good_points,
                "weak_points": weak_points,
            }

    return {
        "id": doc_id,
        "source": "잡코리아",
        "url": url,
        "crawled_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "company": company,
        "position": position,
        "year": year,
        "questions": questions,
        "expert_feedback": expert_feedback,
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    url_list = load_url_list()
    total = len(url_list)
    skipped = 0
    done = 0
    failed = 0

    for i, entry in enumerate(url_list):
        doc_id = entry["id"]
        url = entry["url"]
        out_file = OUTPUT_DIR / f"{doc_id}.json"

        if out_file.exists():
            skipped += 1
            if (i + 1) % 50 == 0:
                print(f"[{i+1}/{total}] skip (exists) {doc_id}")
            continue

        try:
            html = fetch_html(url)
            time.sleep(REQUEST_DELAY_SEC)
            doc = parse_detail_page(html, doc_id, url)
            if doc:
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(doc, f, ensure_ascii=False, indent=2)
                done += 1
            else:
                failed += 1
        except Exception as e:
            failed += 1
            print(f"  fail {doc_id}: {e}")

        if (i + 1) % 20 == 0:
            print(f"[{i+1}/{total}] done={done} skip={skipped} fail={failed}")

    print(f"Finished. done={done} skipped={skipped} failed={failed}")


if __name__ == "__main__":
    main()
