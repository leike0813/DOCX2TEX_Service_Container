from __future__ import annotations

import shutil
import threading
import time

from .cache import CacheStore
from .config import Config
from .database import Database


def _cleanup_old_jobs(cfg: Config, db: Database, retention_days: int) -> None:
    if retention_days <= 0:
        return
    cutoff = time.time() - retention_days * 86400
    ids_to_purge: list[str] = []
    with db.connect() as connection:
        rows = connection.execute(
            (
                "SELECT task_id, COALESCE(end_time, start_time) AS t "
                "FROM tasks WHERE state IN ('done','failed')"
            )
        ).fetchall()
    for row in rows:
        if (row["t"] or 0) < cutoff:
            ids_to_purge.append(row["task_id"])
    for task_id in ids_to_purge:
        shutil.rmtree(cfg.data_root / "tasks" / task_id, ignore_errors=True)
        log_path = cfg.log_dir / f"{task_id}.log"
        if log_path.exists() and (log_path.stat().st_mtime or 0) < cutoff:
            try:
                log_path.unlink()
            except Exception:
                pass
    if ids_to_purge:
        with db.connect() as connection:
            connection.executemany(
                "DELETE FROM tasks WHERE task_id=?",
                [(task_id,) for task_id in ids_to_purge],
            )
            connection.commit()


def _cleanup_caches(db: Database, cache: CacheStore, ttl_days: int) -> None:
    if ttl_days <= 0:
        return
    cutoff = time.time() - ttl_days * 86400
    with db.connect() as connection:
        rows = connection.execute(
            "SELECT cache_key FROM caches WHERE COALESCE(last_access, created) < ?",
            (cutoff,),
        ).fetchall()
    for row in rows:
        key = row["cache_key"]
        try:
            with db.connect() as connection:
                connection.execute("UPDATE caches SET available=0 WHERE cache_key=?", (key,))
                connection.commit()
        except Exception:
            pass
        shutil.rmtree(cache.cache_dir(key), ignore_errors=True)
        try:
            with db.connect() as connection:
                connection.execute("DELETE FROM caches WHERE cache_key=?", (key,))
                connection.commit()
        except Exception:
            pass


def start_cleanup_loop(
    cfg: Config,
    db: Database,
    cache: CacheStore,
    task_retention_days: int | None,
    cache_ttl_days: int | None,
) -> None:
    if task_retention_days is None and cache_ttl_days is None:
        return

    def loop() -> None:
        while True:
            try:
                if task_retention_days is not None:
                    _cleanup_old_jobs(cfg, db, task_retention_days)
            except Exception:
                pass
            try:
                if cache_ttl_days is not None:
                    _cleanup_caches(db, cache, cache_ttl_days)
            except Exception:
                pass
            time.sleep(6 * 3600)

    thread = threading.Thread(target=loop, name="cleanup-loop", daemon=True)
    thread.start()
