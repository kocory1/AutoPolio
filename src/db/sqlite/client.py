"""
SQLite 연결 유틸리티.

프로젝트 기본 DB 경로를 해석하고 aiosqlite connection 생성을 제공한다.
"""

from __future__ import annotations

import os
from pathlib import Path

import aiosqlite
from dotenv import load_dotenv


def resolve_db_path() -> Path:
    """환경변수(`SQLITE_DB_PATH`) 또는 기본값으로 DB 파일 경로를 반환한다."""
    load_dotenv()
    return Path(os.getenv("SQLITE_DB_PATH", "data/autofolio.db"))


async def connect(db_path: str | Path | None = None) -> aiosqlite.Connection:
    """SQLite 비동기 연결을 생성해 반환한다."""
    target = Path(db_path) if db_path else resolve_db_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(target)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA foreign_keys = ON;")
    return conn

