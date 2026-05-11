from __future__ import annotations

import shutil
import threading
import time
from pathlib import Path

from .database import Database
from .storage import atomic_write_json


class CacheStore:
    def __init__(self, db: Database, data_root: Path):
        self.db = db
        self.data_root = data_root

    def get(self, key: str) -> dict[str, str] | None:
        try:
            with self.db.connect() as connection:
                row = connection.execute(
                    "SELECT cache_key, basename, available FROM caches WHERE cache_key=?",
                    (key,),
                ).fetchone()
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
        with self.db.connect() as connection:
            connection.execute(
                (
                    "INSERT OR REPLACE INTO caches(cache_key, basename, created, last_access, "
                    "available) VALUES(?,?,?,?,1)"
                ),
                (key, basename, now, now),
            )
            connection.commit()

    def mark_gone(self, key: str) -> None:
        with self.db.connect() as connection:
            connection.execute("UPDATE caches SET available=0 WHERE cache_key=?", (key,))
            connection.commit()

    def reserve(self, key: str) -> dict[str, str] | None:
        now = time.time()
        with self.db.connect() as connection:
            connection.execute(
                (
                    "INSERT OR IGNORE INTO caches(cache_key, basename, created, last_access, "
                    "available) VALUES(?,?,?,?,0)"
                ),
                (key, "", now, now),
            )
            connection.commit()
            row = connection.execute(
                "SELECT cache_key, basename, available FROM caches WHERE cache_key=?",
                (key,),
            ).fetchone()
        if not row:
            return None
        return {
            "cache_key": row["cache_key"],
            "basename": row["basename"],
            "available": row["available"],
        }

    def publish(self, key: str, basename: str) -> None:
        now = time.time()
        with self.db.connect() as connection:
            connection.execute(
                (
                    "UPDATE caches SET basename=?, available=1, created=?, "
                    "last_access=? WHERE cache_key=?"
                ),
                (basename, now, now, key),
            )
            connection.commit()

    def touch(self, key: str) -> None:
        with self.db.connect() as connection:
            connection.execute(
                "UPDATE caches SET last_access=? WHERE cache_key=?",
                (time.time(), key),
            )
            connection.commit()

    def cache_dir(self, key: str) -> Path:
        return (self.data_root / "cache" / key).resolve()

    def meta_path(self, key: str) -> Path:
        return self.cache_dir(key) / "meta.json"

    def load_meta(self, key: str) -> dict | None:
        meta_path = self.meta_path(key)
        if not meta_path.exists():
            return None
        try:
            import json

            return json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def disk_ok(self, key: str) -> str | None:
        try:
            meta = self.load_meta(key)
            if not meta:
                return None
            basename = meta.get("basename")
            if not basename:
                return None
            cache_dir = self.cache_dir(key)
            required = [
                cache_dir / f"{basename}.tex",
                cache_dir / f"{basename}.xml",
                cache_dir / f"{basename}.debug",
                cache_dir / f"{basename}.docx.tmp",
            ]
            if any(not path.exists() for path in required):
                return None
            return str(basename)
        except Exception:
            return None

    def save_to_disk(self, key: str, basename: str, work_dir: Path) -> None:
        cache_dir = self.cache_dir(key)
        cache_dir.mkdir(parents=True, exist_ok=True)
        for filename in (f"{basename}.tex", f"{basename}.xml", f"{basename}.csv"):
            source = work_dir / filename
            if source.exists():
                shutil.copy2(source, cache_dir / filename)
        for directory in (work_dir / f"{basename}.debug", work_dir / f"{basename}.docx.tmp"):
            if directory.exists():
                destination = cache_dir / directory.name
                if destination.exists():
                    shutil.rmtree(destination, ignore_errors=True)
                shutil.copytree(directory, destination)
        atomic_write_json(
            self.meta_path(key),
            {"key": key, "basename": basename, "created": time.time()},
        )

    def restore_to_work(
        self,
        key: str,
        cached_base: str,
        new_base: str,
        destination: Path,
    ) -> None:
        cache_dir = self.cache_dir(key)
        for extension in ("tex", "xml", "csv"):
            source = cache_dir / f"{cached_base}.{extension}"
            if not source.exists():
                continue
            target = destination / f"{new_base}.{extension}"
            shutil.copy2(source, target)
            if extension == "tex":
                try:
                    text = target.read_text(encoding="utf-8", errors="replace")
                    target.write_text(
                        text.replace(f"{cached_base}.docx.tmp", f"{new_base}.docx.tmp"),
                        encoding="utf-8",
                    )
                except Exception:
                    pass
        for directory_name in (f"{cached_base}.debug", f"{cached_base}.docx.tmp"):
            source_dir = cache_dir / directory_name
            if not source_dir.exists():
                continue
            target_dir = destination / directory_name.replace(cached_base, new_base, 1)
            if target_dir.exists():
                shutil.rmtree(target_dir, ignore_errors=True)
            shutil.copytree(source_dir, target_dir)


class LockManager:
    def __init__(self, db: Database):
        self.db = db

    def claim(self, key: str, builder: str) -> bool:
        try:
            with self.db.connect() as connection:
                connection.execute(
                    "INSERT INTO locks(cache_key,builder,started) VALUES(?,?,?)",
                    (key, builder, time.time()),
                )
                connection.commit()
            return True
        except Exception:
            return False

    def release(self, key: str) -> None:
        try:
            with self.db.connect() as connection:
                connection.execute("DELETE FROM locks WHERE cache_key=?", (key,))
                connection.commit()
        except Exception:
            pass

    def get(self, key: str) -> dict | None:
        try:
            with self.db.connect() as connection:
                row = connection.execute(
                    "SELECT cache_key,builder,started FROM locks WHERE cache_key=?",
                    (key,),
                ).fetchone()
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
        with self.db.connect() as connection:
            rows = connection.execute("SELECT cache_key, started FROM locks").fetchall()
        for row in rows:
            started = row["started"] or 0
            if now - started > max_age_sec:
                self.release(row["cache_key"])

    def start_sweeper(self, interval_sec: int, max_age_sec: int) -> None:
        if interval_sec <= 0:
            return

        def loop() -> None:
            while True:
                try:
                    self.cleanup(max_age_sec)
                except Exception:
                    pass
                time.sleep(max(1, interval_sec))

        thread = threading.Thread(target=loop, name="lock-sweeper", daemon=True)
        thread.start()
