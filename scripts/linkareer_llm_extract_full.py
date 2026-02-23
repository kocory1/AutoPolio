#!/usr/bin/env python3
"""
링커리어 합격 자소서 — 기존 linkareer_crawl_detail.py와 동일한 본문 추출·LLM 로직으로
질문/답변 추출 후 잡코리아 JSON 형식으로 저장.

- data/linkareer_empty_ids.txt 또는 --ids 로 ID 리스트 입력
- 본문: main#coverLetterContent 등 자소서 영역만 추출 (기존과 동일)
- LLM: llm_cover_letter.extract_questions_answers 사용 (기존과 동일)

사용:
  poetry run python scripts/linkareer_llm_extract_full.py   # .env의 OPENAI_API_KEY 사용
  poetry run python scripts/linkareer_llm_extract_full.py --ids 12068 11933
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
PROJECT_ROOT = _SCRIPTS_DIR.parent

LINKAREER_DIR = PROJECT_ROOT / "data" / "linkareer"
URLS_PATH = PROJECT_ROOT / "data" / "linkareer_urls.json"
EMPTY_IDS_PATH = PROJECT_ROOT / "data" / "linkareer_empty_ids.txt"
REQUEST_DELAY_SEC = 1.5
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}
BASE_URL = "https://linkareer.com/cover-letter"


def load_url_map() -> dict[str, str]:
    if not URLS_PATH.exists():
        return {}
    with open(URLS_PATH, encoding="utf-8") as f:
        items = json.load(f)
    return {
        str(item["id"]): item["url"] for item in items if "id" in item and "url" in item
    }


def load_empty_ids() -> List[str]:
    if not EMPTY_IDS_PATH.exists():
        return []
    return [
        line.strip()
        for line in EMPTY_IDS_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def fetch_html(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.text


def extract_body_text(html: str) -> str:
    """기존 linkareer_crawl_detail.py와 동일: 자소서 본문 영역만 추출."""
    soup = BeautifulSoup(html, "html.parser")
    body = (
        soup.select_one("main#coverLetterContent, #coverLetterContent main")
        or soup.select_one(
            "main#coverLetterContent article, #coverLetterContent article"
        )
        or soup.select_one(
            ".cover-letter-content, .cover-letter-body, [class*='CoverLetterDetail']"
        )
        or soup.select_one("main, article")
        or soup.body
    )
    # get_text만 사용, 필터링·정규화 없음
    return body.get_text(separator="\n") if body else ""


def build_jobkorea_format(
    doc_id: str,
    url: str,
    company: str,
    position: str,
    year: str,
    questions: List[dict],
) -> dict:
    """잡코리아 JSON 형식과 동일한 구조로 반환."""
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


def parse_meta_from_html(html: str) -> tuple[str, str, str]:
    """회사·직무·연도 메타 추출 시도."""
    soup = BeautifulSoup(html, "html.parser")
    company = position = year = ""
    title_el = soup.select_one(
        "h1, .cover-letter-title, [class*='title'], .company-name"
    )
    if title_el:
        raw = title_el.get_text(strip=True)
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
    return company, position, year


def main() -> None:
    parser = argparse.ArgumentParser(
        description="링커리어 ID 리스트 → 전체 본문 LLM 추출 → 잡코리아 형식 JSON"
    )
    parser.add_argument(
        "--ids", nargs="*", help="처리할 ID 목록 (없으면 linkareer_empty_ids.txt 사용)"
    )
    parser.add_argument("--limit", type=int, default=0, help="처리 개수 제한 (0=전체)")
    parser.add_argument("--dry-run", action="store_true", help="실제 저장 없이 테스트")
    args = parser.parse_args()

    if args.ids:
        id_list = [str(i) for i in args.ids]
    else:
        id_list = load_empty_ids()
    if args.limit > 0:
        id_list = id_list[: args.limit]
    if not id_list:
        print(
            "처리할 ID가 없습니다. --ids로 지정하거나 linkareer_empty_ids.txt를 확인하세요."
        )
        return

    url_map = load_url_map()
    LINKAREER_DIR.mkdir(parents=True, exist_ok=True)

    done = skip = fail = 0
    total = len(id_list)
    print(f"총 {total}개 ID 처리 시작...")
    for i, doc_id in enumerate(id_list):
        print(f"[{i + 1}/{total}] {doc_id} 처리 중...", end=" ", flush=True)
        url = url_map.get(doc_id) or f"{BASE_URL}/{doc_id}"
        out_file = LINKAREER_DIR / f"{doc_id}.json"
        try:
            html = fetch_html(url)
            time.sleep(REQUEST_DELAY_SEC)
            full_text = extract_body_text(html)
            if len(full_text.strip()) < 50:
                print("본문 짧음, 스킵")
                skip += 1
                continue
            from llm_cover_letter import extract_questions_answers

            try:
                questions = (
                    extract_questions_answers(full_text, source="링커리어") or []
                )
            except Exception as e:
                print(f"LLM 실패 ({e}), 빈 questions로 저장")
                questions = []
            company, position, year = parse_meta_from_html(html)
            doc = build_jobkorea_format(doc_id, url, company, position, year, questions)
            if not args.dry_run:
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(doc, f, ensure_ascii=False, indent=2)
            done += 1
            print("완료")
        except Exception as e:
            fail += 1
            print(f"fail: {e}")
    print(f"Finished. done={done} skip={skip} fail={fail}")


if __name__ == "__main__":
    main()
