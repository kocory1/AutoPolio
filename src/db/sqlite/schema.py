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


def create_all_tables(conn: sqlite3.Connection) -> None:
    """전달받은 sqlite connection에 모든 테이블과 인덱스를 생성한다."""
    conn.execute("PRAGMA foreign_keys = ON;")
    for ddl in DDL_STATEMENTS:
        conn.execute(ddl)
    conn.commit()


async def create_all_tables_async(conn: aiosqlite.Connection) -> None:
    """전달받은 aiosqlite connection에 모든 테이블과 인덱스를 생성한다."""
    await conn.execute("PRAGMA foreign_keys = ON;")
    for ddl in DDL_STATEMENTS:
        await conn.execute(ddl)
    await conn.commit()

