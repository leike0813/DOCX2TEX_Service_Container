from __future__ import annotations

import tempfile
from pathlib import Path

from app.core.db import Database
from app.core.cache import CacheStore, LockManager


def test_cache_db_and_fs_roundtrip():
    with tempfile.TemporaryDirectory() as td:
        data_root = Path(td) / "data"
        data_root.mkdir(parents=True, exist_ok=True)
        db_path = data_root / "state.db"

        db = Database(db_path)
        db.init_schema()
        cache = CacheStore(db, data_root)

        key = "k1"
        # initially no row
        assert cache.get(key) is None
        # reserve creates a row (available=0)
        row = cache.reserve(key)
        assert row and row["cache_key"] == key
        # publish with basename
        cache.publish(key, "base")
        row2 = cache.get(key)
        assert row2 and row2["basename"] == "base"
        cache.touch(key)

        # create a mock work dir with outputs
        work = Path(td) / "work"
        work.mkdir(parents=True, exist_ok=True)
        (work / "base.tex").write_text("\\documentclass{article}", encoding="utf-8")
        (work / "base.xml").write_text("<hub/>", encoding="utf-8")
        (work / "base.debug").mkdir(parents=True, exist_ok=True)
        (work / "base.docx.tmp").mkdir(parents=True, exist_ok=True)

        # save to cache on disk
        cache.save_to_disk(key, "base", work)
        assert cache.disk_ok(key) == "base"

        # restore to a new destination with new basename
        dest = Path(td) / "dest"
        dest.mkdir(parents=True, exist_ok=True)
        cache.restore_to_work(key, "base", "newbase", dest)
        assert (dest / "newbase.tex").exists()


def test_lock_manager_claim_release():
    with tempfile.TemporaryDirectory() as td:
        db = Database(Path(td) / "locks.db")
        db.init_schema()
        lm = LockManager(db)
        key = "ck"
        assert lm.claim(key, "b1") is True
        # second claim should fail while first not released
        assert lm.claim(key, "b2") is False
        assert lm.get(key)["builder"] == "b1"
        lm.release(key)
        assert lm.claim(key, "b3") is True

