#!/usr/bin/env python3
"""
링커리어 상세 수집 결과에서 questions가 비어 있는 문서 id 목록 추출.

사용: poetry run python scripts/linkareer_empty_ids.py
"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
LINKAREER_DIR = PROJECT_ROOT / "data" / "linkareer"
OUTPUT_PATH = PROJECT_ROOT / "data" / "linkareer_empty_ids.txt"


def main() -> None:
    if not LINKAREER_DIR.is_dir():
        print(f"Not a directory: {LINKAREER_DIR}")
        return
    empty_ids: list[str] = []
    for path in sorted(LINKAREER_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            empty_ids.append(path.stem)
            continue
        questions = data.get("questions") or []
        if len(questions) == 0:
            empty_ids.append(data.get("id", path.stem))
    empty_ids.sort(key=int)
    OUTPUT_PATH.write_text("\n".join(empty_ids), encoding="utf-8")
    print(f"Empty (questions=[]): {len(empty_ids)} ids")
    print(f"Saved to {OUTPUT_PATH}")
    if empty_ids:
        print(f"First 20: {empty_ids[:20]}")


if __name__ == "__main__":
    main()
