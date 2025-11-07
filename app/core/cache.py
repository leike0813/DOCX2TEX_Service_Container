from __future__ import annotations

import shutil
import threading
import time
from pathlib import Path
from typing import Optional, Dict

from .db import Database
from .storage import atomic_write_json


class CacheStore:
    """Cache and artifact store abstraction.

    Encapsulates both DB rows in `caches` table and filesystem layout under
    `<data_root>/cache/<cache_key>`.
    """

    def __init__(self, db: Database, data_root: Path):
        self.db = db
        self.data_root = data_root

    # --- DB operations ---
    def get(self, key: str) -> Optional[Dict[str, str]]:
        try:
            with self.db.connect() as con:
                cur = con.execute(
                    "SELECT cache_key, basename, available FROM caches WHERE cache_key=?",
                    (key,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return {
                    "cache_key": row["cache_key"],
                    "basename": row["basename"],
                    "available": row["available"],
                }
        except Exception:
            return None

    def put(self, key: str, basename: str) -> None:
        now = time.time()
        with self.db.connect() as con:
            con.execute(
                "INSERT OR REPLACE INTO caches(cache_key, basename, created, last_access, available) VALUES(?,?,?,?,1)",
                (key, basename, now, now),
            )
            con.commit()

    def mark_gone(self, key: str) -> None:
        with self.db.connect() as con:
            con.execute("UPDATE caches SET available=0 WHERE cache_key=?", (key,))
            con.commit()

    def reserve(self, key: str) -> Optional[Dict[str, str]]:
        now = time.time()
        with self.db.connect() as con:
            con.execute(
                "INSERT OR IGNORE INTO caches(cache_key, basename, created, last_access, available) VALUES(?,?,?,?,0)",
                (key, "", now, now),
            )
            con.commit()
            cur = con.execute(
                "SELECT cache_key, basename, available FROM caches WHERE cache_key=?",
                (key,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {
                "cache_key": row["cache_key"],
                "basename": row["basename"],
                "available": row["available"],
            }

    def publish(self, key: str, basename: str) -> None:
        now = time.time()
        with self.db.connect() as con:
            con.execute(
                "UPDATE caches SET basename=?, available=1, created=?, last_access=? WHERE cache_key=?",
                (basename, now, now, key),
            )
            con.commit()

    def touch(self, key: str) -> None:
        with self.db.connect() as con:
            con.execute("UPDATE caches SET last_access=? WHERE cache_key=?", (time.time(), key))
            con.commit()

    # --- Filesystem helpers ---
    def cache_dir(self, key: str) -> Path:
        return (self.data_root / "cache" / key).resolve()

    def meta_path(self, key: str) -> Path:
        return self.cache_dir(key) / "meta.json"

    def load_meta(self, key: str) -> Optional[dict]:
        meta = self.meta_path(key)
        if not meta.exists():
            return None
        try:
            import json

            return json.loads(meta.read_text(encoding="utf-8"))
        except Exception:
            return None

    def disk_ok(self, key: str) -> Optional[str]:
        try:
            m = self.load_meta(key)
            if not m:
                return None
            base = m.get("basename")
            if not base:
                return None
            d = self.cache_dir(key)
            required = [
                d / f"{base}.tex",
                d / f"{base}.xml",
                d / f"{base}.debug",
                d / f"{base}.docx.tmp",
            ]
            for p in required:
                if not Path(p).exists():
                    return None
            return base
        except Exception:
            return None

    def save_to_disk(self, key: str, basename: str, work: Path) -> None:
        d = self.cache_dir(key)
        d.mkdir(parents=True, exist_ok=True)
        for fn in (f"{basename}.tex", f"{basename}.xml", f"{basename}.csv"):
            p = work / fn
            if p.exists():
                shutil.copy2(p, d / fn)
        src_debug = work / f"{basename}.debug"
        if src_debug.exists():
            dst_debug = d / src_debug.name
            if dst_debug.exists():
                shutil.rmtree(dst_debug, ignore_errors=True)
            shutil.copytree(src_debug, dst_debug)
        src_tmp = work / f"{basename}.docx.tmp"
        if src_tmp.exists():
            dst_tmp = d / src_tmp.name
            if dst_tmp.exists():
                shutil.rmtree(dst_tmp, ignore_errors=True)
            shutil.copytree(src_tmp, dst_tmp)
        meta = {"key": key, "basename": basename, "created": time.time()}
        atomic_write_json(self.meta_path(key), meta)

    def restore_to_work(self, key: str, cached_base: str, new_base: str, dest: Path) -> None:
        d = self.cache_dir(key)
        # files
        for ext in ("tex", "xml", "csv"):
            src = d / f"{cached_base}.{ext}"
            if src.exists():
                dst = dest / f"{new_base}.{ext}"
                shutil.copy2(src, dst)
                if ext == "tex":
                    try:
                        s = dst.read_text(encoding="utf-8", errors="replace")
                        s = s.replace(f"{cached_base}.docx.tmp", f"{new_base}.docx.tmp")
                        dst.write_text(s, encoding="utf-8")
                    except Exception:
                        pass
        # debug dir
        src_debug = d / f"{cached_base}.debug"
        if src_debug.exists():
            dst_debug = dest / f"{new_base}.debug"
            if dst_debug.exists():
                shutil.rmtree(dst_debug, ignore_errors=True)
            shutil.copytree(src_debug, dst_debug)
        # tmp dir
        src_tmp = d / f"{cached_base}.docx.tmp"
        if src_tmp.exists():
            dst_tmp = dest / f"{new_base}.docx.tmp"
            if dst_tmp.exists():
                shutil.rmtree(dst_tmp, ignore_errors=True)
            shutil.copytree(src_tmp, dst_tmp)


class LockManager:
    """Lock helper for cache builds (rows in `locks`)."""

    def __init__(self, db: Database):
        self.db = db

    def claim(self, key: str, builder: str) -> bool:
        try:
            with self.db.connect() as con:
                con.execute(
                    "INSERT INTO locks(cache_key,builder,started) VALUES(?,?,?)",
                    (key, builder, time.time()),
                )
                con.commit()
                return True
        except Exception:
            return False

    def release(self, key: str) -> None:
        try:
            with self.db.connect() as con:
                con.execute("DELETE FROM locks WHERE cache_key=?", (key,))
                con.commit()
        except Exception:
            pass

    def get(self, key: str) -> Optional[dict]:
        try:
            with self.db.connect() as con:
                cur = con.execute(
                    "SELECT cache_key,builder,started FROM locks WHERE cache_key=?",
                    (key,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return {
                    "cache_key": row["cache_key"],
                    "builder": row["builder"],
                    "started": row["started"],
                }
        except Exception:
            return None

    def cleanup(self, max_age_sec: int) -> None:
        if max_age_sec <= 0:
            return
        now = time.time()
        with self.db.connect() as con:
            cur = con.execute("SELECT cache_key, started FROM locks")
            rows = cur.fetchall()
        for row in rows:
            started = row["started"] or 0
            if now - started > max_age_sec:
                self.release(row["cache_key"])

    def start_sweeper(self, interval_sec: int, max_age_sec: int) -> None:
        if interval_sec <= 0:
            return

        def loop():
            while True:
                try:
                    self.cleanup(max_age_sec)
                except Exception:
                    pass
                time.sleep(max(1, interval_sec))

        t = threading.Thread(target=loop, name="lock-sweeper", daemon=True)
        t.start()

