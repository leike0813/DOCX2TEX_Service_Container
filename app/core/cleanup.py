from __future__ import annotations

import shutil
import threading
import time
from pathlib import Path
from typing import Optional

from .config import Config
from .db import Database
from .cache import CacheStore


def _cleanup_old_jobs(cfg: Config, db: Database, retention_days: int) -> None:
    if retention_days <= 0:
        return
    cutoff = time.time() - retention_days * 86400
    ids_to_purge: list[str] = []
    with db.connect() as con:
        cur = con.execute(
            "SELECT task_id, COALESCE(end_time, start_time) AS t FROM tasks WHERE state IN ('done','failed')"
        )
        for row in cur.fetchall():
            if (row["t"] or 0) < cutoff:
                ids_to_purge.append(row["task_id"])
    # Filesystem cleanup first
    for tid in ids_to_purge:
        d = cfg.data_root / "tasks" / tid
        if d.exists():
            try:
                shutil.rmtree(d, ignore_errors=True)
            except Exception:
                pass
        log_path = cfg.log_dir / f"{tid}.log"
        if log_path.exists() and (log_path.stat().st_mtime or 0) < cutoff:
            try:
                log_path.unlink()
            except Exception:
                pass
    if ids_to_purge:
        with db.connect() as con:
            con.executemany("DELETE FROM tasks WHERE task_id=?", [(i,) for i in ids_to_purge])
            con.commit()


def _cleanup_caches(cfg: Config, db: Database, cache: CacheStore, ttl_days: int) -> None:
    if ttl_days <= 0:
        return
    cutoff = time.time() - ttl_days * 86400
    with db.connect() as con:
        cur = con.execute(
            "SELECT cache_key, basename, COALESCE(last_access, created) AS t, available FROM caches WHERE COALESCE(last_access, created) < ?",
            (cutoff,),
        )
        rows = cur.fetchall()
    for row in rows:
        key = row["cache_key"]
        try:
            # mark unavailable to avoid races
            with db.connect() as con:
                con.execute("UPDATE caches SET available=0 WHERE cache_key=?", (key,))
                con.commit()
        except Exception:
            pass
        # delete filesystem safely
        d = cache.cache_dir(key)
        try:
            if d.exists():
                shutil.rmtree(d, ignore_errors=True)
        except Exception:
            continue
        # delete db row
        try:
            with db.connect() as con:
                con.execute("DELETE FROM caches WHERE cache_key=?", (key,))
                con.commit()
        except Exception:
            pass


def start_cleanup_loop(cfg: Config, db: Database, cache: CacheStore, task_retention_days: Optional[int], cache_ttl_days: Optional[int]) -> None:
    if task_retention_days is None and cache_ttl_days is None:
        return

    def loop():
        while True:
            try:
                if task_retention_days is not None:
                    _cleanup_old_jobs(cfg, db, task_retention_days)
            except Exception:
                pass
            try:
                if cache_ttl_days is not None:
                    _cleanup_caches(cfg, db, cache, cache_ttl_days)
            except Exception:
                pass
            time.sleep(6 * 3600)

    t = threading.Thread(target=loop, name="cleanup-loop", daemon=True)
    t.start()

