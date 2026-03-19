"""
Autofolio SQLite 스키마 생성 유틸.

문서(`AUTOFOLIO_DB_스키마_설계.md`) 기준으로 테이블을 생성한다.
"""

from __future__ import annotations

import sqlite3

import aiosqlite


DDL_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        github_username TEXT,
        github_id INTEGER,
        email TEXT,
        avatar_url TEXT,
        access_token TEXT,
        created_at DATETIME,
        updated_at DATETIME
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY,
        url TEXT NOT NULL,
        duty TEXT,
        qualifications TEXT,
        preferred TEXT,
        company_name TEXT,
        company_values TEXT,
        position TEXT,
        questions TEXT,
        created_at DATETIME
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS selected_repos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        repo_full_name TEXT NOT NULL,
        created_at DATETIME,
        FOREIGN KEY(user_id) REFERENCES users(id),
        UNIQUE(user_id, repo_full_name)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS selected_repo_assets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        selected_repo_id INTEGER NOT NULL,
        asset_type TEXT NOT NULL CHECK(asset_type IN ('code', 'folder')),
        repo_path TEXT NOT NULL,
        created_at DATETIME,
        FOREIGN KEY(selected_repo_id) REFERENCES selected_repos(id) ON DELETE CASCADE,
        UNIQUE(selected_repo_id, asset_type, repo_path)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS asset_hierarchy (
        id TEXT PRIMARY KEY,
        selected_repo_id INTEGER NOT NULL,
        type TEXT NOT NULL CHECK(type IN ('code', 'folder', 'project')),
        parent_id TEXT,
        FOREIGN KEY(selected_repo_id) REFERENCES selected_repos(id) ON DELETE CASCADE,
        FOREIGN KEY(parent_id) REFERENCES asset_hierarchy(id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS cover_letters (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        draft TEXT,
        question TEXT,
        max_chars INTEGER,
        job_id TEXT,
        thread_id TEXT,
        round INTEGER,
        created_at DATETIME,
        updated_at DATETIME,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(job_id) REFERENCES jobs(id)
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS portfolios (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL,
        name TEXT,
        description TEXT,
        content TEXT,
        created_at DATETIME,
        updated_at DATETIME,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_cover_letters_user_id
    ON cover_letters(user_id);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_cover_letters_job_id
    ON cover_letters(job_id);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_selected_repos_user_id
    ON selected_repos(user_id);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_selected_repo_assets_selected_repo_id
    ON selected_repo_assets(selected_repo_id);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_asset_hierarchy_selected_repo_id
    ON asset_hierarchy(selected_repo_id);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_asset_hierarchy_parent_id
    ON asset_hierarchy(parent_id);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_portfolios_user_id
    ON portfolios(user_id);
    """,
)


def _ensure_users_columns_sync(conn: sqlite3.Connection) -> None:
    """기존 DB에 users 컬럼이 없을 때 마이그레이션(ALTER TABLE)을 수행한다."""
    cursor = conn.execute("PRAGMA table_info(users);")
    existing = {row[1] for row in cursor.fetchall()}  # row = (cid, name, type, ...)

    # (column_name, column_type)
    needed = [
        ("github_id", "INTEGER"),
        ("email", "TEXT"),
        ("avatar_url", "TEXT"),
    ]
    for col, typ in needed:
        if col not in existing:
            conn.execute(f"ALTER TABLE users ADD COLUMN {col} {typ};")


async def _ensure_users_columns_async(conn: aiosqlite.Connection) -> None:
    """async 환경에서 기존 DB users 컬럼 존재 여부를 확인/추가한다."""
    cursor = await conn.execute("PRAGMA table_info(users);")
    rows = await cursor.fetchall()
    existing = {row[1] for row in rows}

    needed = [
        ("github_id", "INTEGER"),
        ("email", "TEXT"),
        ("avatar_url", "TEXT"),
    ]
    for col, typ in needed:
        if col not in existing:
            await conn.execute(f"ALTER TABLE users ADD COLUMN {col} {typ};")


def create_all_tables(conn: sqlite3.Connection) -> None:
    """전달받은 sqlite connection에 모든 테이블과 인덱스를 생성한다."""
    conn.execute("PRAGMA foreign_keys = ON;")
    for ddl in DDL_STATEMENTS:
        conn.execute(ddl)
    # CREATE TABLE IF NOT EXISTS만으로는 기존 DB의 스키마 변경이 안 된다.
    _ensure_users_columns_sync(conn)
    conn.commit()


async def create_all_tables_async(conn: aiosqlite.Connection) -> None:
    """전달받은 aiosqlite connection에 모든 테이블과 인덱스를 생성한다."""
    await conn.execute("PRAGMA foreign_keys = ON;")
    for ddl in DDL_STATEMENTS:
        await conn.execute(ddl)
    # 기존 DB에 컬럼이 없다면 ALTER TABLE로 보강한다.
    await _ensure_users_columns_async(conn)
    await conn.commit()

