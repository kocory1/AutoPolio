#!/usr/bin/env python3
"""
링커리어 합격 자소서 상세 수집 스크립트 (2단계) — LLM 사용

- data/linkareer_urls.json 의 URL 목록을 읽어서
- 각 상세 페이지 요청 → 본문 텍스트 추출 후 LLM으로 문항/답변 추출
- data/linkareer/{id}.json 저장 (이미 있으면 스킵)
- OPENAI_API_KEY 환경변수 필요.

사용: OPENAI_API_KEY=sk-... poetry run python scripts/linkareer_crawl_detail.py
"""

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional

import requests
from bs4 import BeautifulSoup

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
PROJECT_ROOT = _SCRIPTS_DIR.parent
URLS_PATH = PROJECT_ROOT / "data" / "linkareer_urls.json"
OUTPUT_DIR = PROJECT_ROOT / "data" / "linkareer"
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


def parse_detail_page(html: str, doc_id: str, url: str) -> Optional[Any]:
    soup = BeautifulSoup(html, "html.parser")

    company = ""
    position = ""
    year = ""

    # 회사명·직무·연도: 링커리어 페이지 구조에 맞는 선택자 (실제 수집 후 조정 가능)
    title_el = soup.select_one("h1, .cover-letter-title, [class*='title'], .company-name")
    if title_el:
        raw = title_el.get_text(strip=True)
        # "회사명 · 연도 직무" 등 패턴 가정
        if "·" in raw:
            parts = [p.strip() for p in raw.split("·", 2)]
            if len(parts) >= 1:
                company = parts[0]
            if len(parts) >= 2:
                year = parts[1]
            if len(parts) >= 3:
                position = parts[2]
        else:
            company = raw

    # 별도 메타/헤더에서 회사·직무·연도 추출 시도
    if not company:
        company_el = soup.select_one("[class*='company'], [class*='Company']")
        if company_el:
            company = company_el.get_text(strip=True)
    if not position:
        pos_el = soup.select_one("[class*='position'], [class*='role'], [class*='직무']")
        if pos_el:
            position = pos_el.get_text(strip=True)
    if not year:
        year_el = soup.select_one("[class*='year'], [class*='연도'], [class*='passed']")
        if year_el:
            year = year_el.get_text(strip=True)

    # 본문 텍스트 추출 → LLM으로 문항/답변 추출
    body = (
        soup.select_one("main#coverLetterContent, #coverLetterContent main")
        or soup.select_one("main#coverLetterContent article, #coverLetterContent article")
        or soup.select_one(".cover-letter-content, .cover-letter-body, [class*='CoverLetterDetail']")
        or soup.select_one("main, article")
        or soup.body
    )
    body_text = body.get_text(separator="\n") if body else ""
    questions: List[dict] = []
    try:
        from llm_cover_letter import extract_questions_answers
        extracted = extract_questions_answers(body_text, source="링커리어")
        if extracted:
            questions = extracted
    except Exception:
        # OPENAI_API_KEY 없음 / API 오류 시 빈 리스트로 저장
        pass

    return {
        "id": doc_id,
        "source": "링커리어",
        "url": url,
        "crawled_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "company": company,
        "position": position,
        "year": year,
        "questions": questions,
        "expert_feedback": None,
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not URLS_PATH.exists():
        print(f"URL list not found: {URLS_PATH}. Run linkareer_collect_urls.py first.")
        return
    url_list = load_url_list()
    total = len(url_list)
    skipped = done = failed = 0

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
