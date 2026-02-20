#!/usr/bin/env python3
"""
잡코리아 합격 자소서 상세 URL 수집 스크립트 (1단계)

- 리스트 페이지를 페이지네이션하며 순회
- 각 페이지에서 상세 URL(/starter/PassAssay/View/{id}) 추출
- data/jobkorea_urls.json 에 [{ id, url }, ...] 형태로 저장

사용: python scripts/jobkorea_collect_urls.py
"""

import json
import re
import time
from pathlib import Path
from typing import List

import requests
from bs4 import BeautifulSoup

# --- 설정 ---
BASE_LIST_URL = (
    "https://www.jobkorea.co.kr/starter/PassAssay"
    "?schPart=10031&schWork=&schEduLevel=&schCType=&schGroup="
    "&isSaved=1&isFilterChecked=1&OrderBy=0&schTxt="
)
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "jobkorea_urls.json"
REQUEST_DELAY_SEC = 1.5  # 요청 간 딜레이 (rate limit 고려)
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
}


def get_list_page(page: int) -> str:
    """리스트 페이지 HTML 반환. page=1이면 파라미터 없음, 2부터는 &Page=N."""
    url = BASE_LIST_URL if page <= 1 else f"{BASE_LIST_URL}&Page={page}"
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.text


def extract_detail_urls(html: str) -> List[dict]:
    """HTML에서 상세 페이지 링크 추출. 반환: [{"id": "199325", "url": "https://..."}, ...]"""
    soup = BeautifulSoup(html, "html.parser")
    seen_ids = set()
    items = []

    # /starter/PassAssay/View/숫자 형태 링크 수집
    pattern = re.compile(r"/starter/PassAssay/View/(\d+)")
    for a in soup.find_all("a", href=True):
        m = pattern.search(a["href"])
        if not m:
            continue
        doc_id = m.group(1)
        if doc_id in seen_ids:
            continue
        seen_ids.add(doc_id)
        full_url = a["href"] if a["href"].startswith("http") else f"https://www.jobkorea.co.kr{a['href']}"
        items.append({"id": doc_id, "url": full_url})

    return items


def has_next_button(html: str) -> bool:
    """다음 페이지 버튼 존재 여부."""
    soup = BeautifulSoup(html, "html.parser")
    next_btn = soup.select_one("a.tplBtn.btnPgnNext, a.btnPgnNext")
    return next_btn is not None and "href" in next_btn.attrs


def main() -> None:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    all_entries = []
    page = 1

    while True:
        print(f"Fetching list page {page}...")
        html = get_list_page(page)
        time.sleep(REQUEST_DELAY_SEC)

        entries = extract_detail_urls(html)
        if not entries:
            print(f"Page {page}: no detail links found, stopping.")
            break

        for e in entries:
            if not any(x["id"] == e["id"] for x in all_entries):
                all_entries.append(e)

        print(f"  -> {len(entries)} links (total unique: {len(all_entries)})")

        if not has_next_button(html):
            print("No next button, pagination done.")
            break

        page += 1

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_entries, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(all_entries)} URLs to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
