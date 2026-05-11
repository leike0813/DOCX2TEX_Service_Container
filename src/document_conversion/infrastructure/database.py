from __future__ import annotations

import sqlite3
from pathlib import Path


class Database:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(str(self.db_path), check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL;")
        connection.execute("PRAGMA synchronous=NORMAL;")
        connection.execute("PRAGMA busy_timeout=5000;")
        return connection

    def init_schema(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.execute(
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
            connection.execute(
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
            try:
                connection.execute("ALTER TABLE caches ADD COLUMN last_access REAL")
            except Exception:
                pass
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS locks (
                  cache_key TEXT PRIMARY KEY,
                  builder   TEXT,
                  started   REAL
                );
                """
            )
            connection.commit()
