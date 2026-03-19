from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def get_dashboard_html() -> str:
    """
    `src/app/main.py` 내부에 존재하던 `dashboard_html` 블록을 추출해 제공한다.

    - 목적: 라우트가 프론트 소스를 `src/web`에서 참조하도록 디렉토리 구조를 정리하기 위함.
    - 향후 `main.py`에서 실제 문자열을 제거/이관하면 이 추출 로직은 생략할 수 있다.
    """
    main_py = Path(__file__).resolve().parents[1] / "app" / "main.py"
    text = main_py.read_text(encoding="utf-8")

    # main.py 내에서 dashboard_html = """ ... """ .strip() 형태를 캡처
    m = re.search(
        r'dashboard_html\s*=\s*"""(.*?)"""\s*\.strip\(\)',
        text,
        flags=re.S,
    )
    if not m:
        raise RuntimeError("Could not extract dashboard_html from src/app/main.py")
    return m.group(1)


dashboard_html = get_dashboard_html()

