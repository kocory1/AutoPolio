#!/usr/bin/env python3
"""
비어 있던 링커리어 id만 재수집 (linkareer_empty_ids.txt 기준).
기존 JSON 덮어쓰기.

사용: poetry run python scripts/linkareer_retry_empty.py
"""

import json
import sys
import time
from pathlib import Path

# 상세 파싱 로직 재사용
sys.path.insert(0, str(Path(__file__).resolve().parent))
from linkareer_crawl_detail import (
    OUTPUT_DIR,
    REQUEST_DELAY_SEC,
    fetch_html,
    load_url_list,
    parse_detail_page,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
EMPTY_IDS_PATH = PROJECT_ROOT / "data" / "linkareer_empty_ids.txt"


def main() -> None:
    if not EMPTY_IDS_PATH.exists():
        print(f"Not found: {EMPTY_IDS_PATH}. Run linkareer_empty_ids.py first.")
        return
    empty_ids = [line.strip() for line in EMPTY_IDS_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    url_list = load_url_list()
    id_to_url = {e["id"]: e["url"] for e in url_list}
    todo = [(id_, id_to_url[id_]) for id_ in empty_ids if id_ in id_to_url]
    missing = [id_ for id_ in empty_ids if id_ not in id_to_url]
    if missing:
        print(f"URL 목록에 없는 id ({len(missing)}): {missing[:10]}...")
    print(f"Re-crawling {len(todo)} ids...")
    done = failed = 0
    for i, (doc_id, url) in enumerate(todo):
        try:
            html = fetch_html(url)
            time.sleep(REQUEST_DELAY_SEC)
            doc = parse_detail_page(html, doc_id, url)
            if doc:
                out_file = OUTPUT_DIR / f"{doc_id}.json"
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(doc, f, ensure_ascii=False, indent=2)
                done += 1
                q_count = len(doc.get("questions") or [])
                if q_count == 0:
                    print(f"  {doc_id} still 0 questions")
            else:
                failed += 1
        except Exception as e:
            failed += 1
            print(f"  fail {doc_id}: {e}")
        if (i + 1) % 30 == 0:
            print(f"  [{i+1}/{len(todo)}] done={done} fail={failed}")
    print(f"Finished. done={done} failed={failed}")


if __name__ == "__main__":
    main()
