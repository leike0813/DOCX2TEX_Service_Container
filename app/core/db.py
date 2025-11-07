from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional


class Database:
    """SQLite database helper with schema initialization.

    Mirrors the schema used by server.py and provides methods to create
    connections with sane defaults for concurrency.
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path

    def connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(str(self.db_path), check_same_thread=False)
        con.row_factory = sqlite3.Row
        # Improve concurrency
        con.execute("PRAGMA journal_mode=WAL;")
        con.execute("PRAGMA synchronous=NORMAL;")
        con.execute("PRAGMA busy_timeout=5000;")
        return con

    def init_schema(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as con:
            # Tasks table
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                  task_id TEXT PRIMARY KEY,
                  state TEXT NOT NULL,
                  err_msg TEXT DEFAULT '',
                  start_time REAL NOT NULL,
                  end_time REAL,
                  debug INTEGER NOT NULL,
                  img_post_proc INTEGER NOT NULL,
                  work_dir TEXT NOT NULL,
                  created REAL NOT NULL,
                  sha256 TEXT
                );
                """
            )
            # Caches table
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS caches (
                  cache_key TEXT PRIMARY KEY,
                  basename TEXT NOT NULL,
                  created REAL NOT NULL,
                  last_access REAL NOT NULL,
                  available INTEGER NOT NULL DEFAULT 1
                );
                """
            )
            # Ensure last_access column exists (for upgrades)
            try:
                con.execute("ALTER TABLE caches ADD COLUMN last_access REAL")
            except Exception:
                pass
            # Locks table
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS locks (
                  cache_key TEXT PRIMARY KEY,
                  builder   TEXT,
                  started   REAL
                );
                """
            )
            con.commit()

