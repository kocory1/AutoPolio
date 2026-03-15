"""
Autofolio SQLite 테이블 생성 스크립트.

실행:
    poetry run python -m scripts.init_sqlite_db
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from src.db.sqlite import connect, create_all_tables_async
from dotenv import load_dotenv


def resolve_db_path() -> Path:
    """환경변수/기본값을 기준으로 SQLite DB 파일 경로를 반환한다."""
    load_dotenv()
    raw_path = os.getenv("SQLITE_DB_PATH", "data/autofolio.db")
    db_path = Path(raw_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return db_path


async def main() -> None:
    """DB 파일을 만들고 테이블을 초기화한다."""
    db_path = resolve_db_path()

    conn = await connect(db_path)
    try:
        await create_all_tables_async(conn)
    finally:
        await conn.close()

    print(f"[OK] SQLite schema created: {db_path}")


if __name__ == "__main__":
    asyncio.run(main())

