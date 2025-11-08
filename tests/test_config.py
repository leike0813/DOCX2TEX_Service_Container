from __future__ import annotations

import os
from pathlib import Path
import tempfile

from app.core.config import Config


def test_config_from_env_defaults(monkeypatch=None):
    # Clear env for controlled defaults
    for k in [
        "APP_HOME",
        "DATA_ROOT",
        "WORK_ROOT",
        "LOG_DIR",
        "DOCX2TEX_HOME",
        "XML_CATALOG_FILES",
        "STATE_DB",
        "MAX_UPLOAD_BYTES",
        "UVICORN_WORKERS",
        "TTL_DAYS",
        "LOCK_SWEEP_INTERVAL_SEC",
        "LOCK_MAX_AGE_SEC",
    ]:
        os.environ.pop(k, None)

    cfg = Config.from_env()
    # Paths resolve and are Path instances
    assert isinstance(cfg.app_home, Path)
    assert isinstance(cfg.data_root, Path)
    assert isinstance(cfg.public_root, Path)
    assert isinstance(cfg.log_dir, Path)
    assert isinstance(cfg.docx2tex_home, Path)
    assert isinstance(cfg.catalog_file, Path)
    assert isinstance(cfg.db_path, Path)
    # Ints and optionals
    assert isinstance(cfg.max_upload_bytes, int)
    assert isinstance(cfg.uvicorn_workers, int)
    assert (cfg.ttl_days is None) or isinstance(cfg.ttl_days, int)
    assert isinstance(cfg.lock_sweep_interval_sec, int)
    assert isinstance(cfg.lock_max_age_sec, int)


def test_config_overrides(monkeypatch=None):
    with tempfile.TemporaryDirectory() as td:
        base = Path(td) / "x"
        os.environ["APP_HOME"] = str(base / "app")
        os.environ["DATA_ROOT"] = str(base / "data")
        os.environ["WORK_ROOT"] = str(base / "work")
        os.environ["LOG_DIR"] = str(base / "logs")
        os.environ["DOCX2TEX_HOME"] = str(base / "docx2tex")
        os.environ["XML_CATALOG_FILES"] = str(base / "catalog.xml")
        os.environ["STATE_DB"] = str(base / "state.db")
        os.environ["MAX_UPLOAD_BYTES"] = "1234"
        os.environ["UVICORN_WORKERS"] = "3"
        os.environ["TTL_DAYS"] = "9"
        os.environ["LOCK_SWEEP_INTERVAL_SEC"] = "5"
        os.environ["LOCK_MAX_AGE_SEC"] = "99"

        cfg = Config.from_env()
        # Be robust across Windows/POSIX path styles
        assert cfg.app_home == (base / "app").resolve()
        assert cfg.data_root == (base / "data").resolve()
        assert cfg.public_root == (base / "work").resolve()
        assert cfg.log_dir == (base / "logs").resolve()
        assert cfg.docx2tex_home == (base / "docx2tex").resolve()
        assert cfg.catalog_file == (base / "catalog.xml").resolve()
        assert cfg.db_path == (base / "state.db").resolve()
        assert cfg.max_upload_bytes == 1234
        assert cfg.uvicorn_workers == 3
        assert cfg.ttl_days == 9
        assert cfg.lock_sweep_interval_sec == 5
        assert cfg.lock_max_age_sec == 99
    for k in [
        "APP_HOME",
        "DATA_ROOT",
        "WORK_ROOT",
        "LOG_DIR",
        "DOCX2TEX_HOME",
        "XML_CATALOG_FILES",
        "STATE_DB",
        "MAX_UPLOAD_BYTES",
        "UVICORN_WORKERS",
        "TTL_DAYS",
        "LOCK_SWEEP_INTERVAL_SEC",
        "LOCK_MAX_AGE_SEC",
    ]:
        os.environ.pop(k, None)
