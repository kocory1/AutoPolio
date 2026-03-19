"""
포트폴리오 저장/조회 서비스.

SQLite `portfolios` 테이블에 포트폴리오 JSON(content)을 저장하고 조회한다.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from src.db.sqlite import connect


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


async def create_portfolio(
    user_id: str,
    content: dict,
    name: str = "auto-generated",
    db_path: str | Path | None = None,
) -> dict:
    """포트폴리오를 저장하고 메타데이터를 반환한다."""
    portfolio_id = str(uuid4())
    now = _utc_now_iso()
    content_json = json.dumps(content, ensure_ascii=False)

    conn = await connect(db_path)
    try:
        await conn.execute(
            """
            INSERT INTO portfolios (id, user_id, name, content, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (portfolio_id, user_id, name, content_json, now, now),
        )
        await conn.commit()
    finally:
        await conn.close()

    return {
        "portfolio_id": portfolio_id,
        "user_id": user_id,
        "created_at": now,
        "updated_at": now,
    }


async def get_portfolio_by_id(
    user_id: str,
    portfolio_id: str,
    db_path: str | Path | None = None,
) -> dict | None:
    """유저의 단건 포트폴리오를 조회한다."""
    conn = await connect(db_path)
    try:
        cursor = await conn.execute(
            """
            SELECT id, user_id, name, description, content, created_at, updated_at
            FROM portfolios
            WHERE user_id = ? AND id = ?
            """,
            (user_id, portfolio_id),
        )
        row = await cursor.fetchone()
        await cursor.close()
    finally:
        await conn.close()

    if row is None:
        return None

    try:
        portfolio_content = json.loads(row["content"]) if row["content"] else {}
    except json.JSONDecodeError:
        portfolio_content = {}

    return {
        "portfolio_id": row["id"],
        "user_id": row["user_id"],
        "name": row["name"],
        "description": row["description"],
        "portfolio": portfolio_content,
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


async def list_portfolios(
    user_id: str,
    db_path: str | Path | None = None,
) -> list[dict]:
    """유저의 포트폴리오 목록을 조회한다."""
    conn = await connect(db_path)
    try:
        cursor = await conn.execute(
            """
            SELECT id, created_at, updated_at
            FROM portfolios
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        )
        rows = await cursor.fetchall()
        await cursor.close()
    finally:
        await conn.close()

    return [
        {
            "portfolio_id": row["id"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]

