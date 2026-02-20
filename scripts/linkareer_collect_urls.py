#!/usr/bin/env python3
"""
링커리어 합격 자소서 상세 URL 수집 스크립트 (1단계)

- 검색 결과가 JS 렌더링이므로 Playwright 사용.
- 직무 키워드 리스트별로 검색 페이지 접속 → 렌더 대기 → /cover-letter/{id} 링크 추출
- 페이지네이션: MUI 방식 — "다음" 버튼 또는 페이지 번호 버튼(button-page-number) 클릭
- id 기준 중복 제거 후 data/linkareer_urls.json 저장

사용:
  poetry install && poetry run playwright install
  poetry run python scripts/linkareer_collect_urls.py
"""

import json
import re
import time
from pathlib import Path
from typing import List
from urllib.parse import urlencode, urljoin

ROLE_KEYWORDS = [
    "개발자",
    "백엔드",
    "프론트엔드",
    "풀스택",
    "네트워크",
    "AI",
    "딥러닝",
    "데이터",
    "머신러닝",
    "LLM",
    "SW",
    "java",
    "python",
]

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "linkareer_urls.json"
REQUEST_DELAY_SEC = 1.5
BASE_URL = "https://linkareer.com"
WAIT_FOR_LIST_MS = 8000


def get_search_url(keyword: str, page: int = 1) -> str:
    params = {"role": keyword, "sort": "PASSED_AT"}
    if page > 1:
        params["page"] = page
    return f"{BASE_URL}/cover-letter/search?{urlencode(params)}"


def extract_detail_urls_from_page(page) -> List[dict]:
    id_pattern = re.compile(r"^/cover-letter/(\d+)(?:\?|$)")
    seen = set()
    items: List[dict] = []
    for a in page.query_selector_all('a[href*="/cover-letter/"]'):
        href = a.get_attribute("href") or ""
        if not href.startswith("/cover-letter/"):
            continue
        m = id_pattern.match(href.split("?")[0])
        if not m:
            continue
        doc_id = m.group(1)
        if doc_id in seen:
            continue
        seen.add(doc_id)
        full_url = urljoin(BASE_URL, href.split("?")[0])
        if not full_url.startswith("http"):
            full_url = f"{BASE_URL}/cover-letter/{doc_id}"
        items.append({"id": doc_id, "url": full_url})
    return items


def go_to_next_page(page, current_page_num: int) -> bool:
    """
    MUI 페이지네이션: 다음 버튼(aria-label) 또는 페이지 번호 버튼(button-page-number) 클릭.
    성공 시 True, 더 이상 다음 페이지 없으면 False.
    """
    next_page_num = current_page_num + 1
    # 1) "다음" 버튼 (비활성 아닌 것)
    next_btn = page.locator(
        'button[aria-label="Go to next page"], button[aria-label="다음 페이지"]'
    ).first
    if next_btn.count() > 0:
        try:
            if next_btn.is_visible() and "Mui-disabled" not in (
                next_btn.get_attribute("class") or ""
            ):
                next_btn.click()
                page.wait_for_timeout(1500)
                return True
        except Exception:
            pass
    # 2) 페이지 번호 버튼 클릭 (button.button-page-number 안의 span.MuiButton-label 숫자)
    page_num_btn = (
        page.locator("button.button-page-number")
        .filter(has_text=str(next_page_num))
        .first
    )
    try:
        if page_num_btn.count() > 0 and page_num_btn.is_visible():
            page_num_btn.click()
            page.wait_for_timeout(1500)
            return True
    except Exception:
        pass
    return False


def collect_urls_for_keyword(page, keyword: str, seen_ids: set) -> List[dict]:
    collected: List[dict] = []
    page_num = 1
    max_pages = 100
    url = get_search_url(keyword, 1)
    page.goto(url, wait_until="domcontentloaded", timeout=20000)
    page.wait_for_timeout(WAIT_FOR_LIST_MS)

    while page_num <= max_pages:
        entries = extract_detail_urls_from_page(page)
        if not entries:
            break
        added = 0
        for e in entries:
            if e["id"] not in seen_ids:
                seen_ids.add(e["id"])
                collected.append(e)
                added += 1
        if not go_to_next_page(page, page_num):
            break
        page_num += 1
    return collected


def main() -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "Playwright 미설치. 실행: poetry install && poetry run playwright install"
        )
        return

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    all_entries: List[dict] = []
    seen_ids = set()

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
        except Exception as e:
            if "Executable doesn't exist" in str(e) or "playwright" in str(e).lower():
                print(
                    "Playwright 브라우저가 로컬에 없습니다. 아래를 터미널에서 실행하세요:"
                )
                print("  poetry run playwright install")
                return
            raise
        context = browser.new_context(
            locale="ko-KR",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )
        page = context.new_page()
        try:
            for keyword in ROLE_KEYWORDS:
                print(f"Keyword: {keyword}")
                try:
                    new_ones = collect_urls_for_keyword(page, keyword, seen_ids)
                    all_entries.extend(new_ones)
                    print(
                        f"  -> +{len(new_ones)} links (total unique: {len(all_entries)})"
                    )
                except Exception as e:
                    print(f"  Error: {e}")
                time.sleep(REQUEST_DELAY_SEC)
        finally:
            browser.close()

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(all_entries, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(all_entries)} URLs to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
