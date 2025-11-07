from __future__ import annotations

import os
from pathlib import Path

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
    os.environ["APP_HOME"] = "/x/app"
    os.environ["DATA_ROOT"] = "/x/data"
    os.environ["WORK_ROOT"] = "/x/work"
    os.environ["LOG_DIR"] = "/x/logs"
    os.environ["DOCX2TEX_HOME"] = "/x/docx2tex"
    os.environ["XML_CATALOG_FILES"] = "/x/catalog.xml"
    os.environ["STATE_DB"] = "/x/state.db"
    os.environ["MAX_UPLOAD_BYTES"] = "1234"
    os.environ["UVICORN_WORKERS"] = "3"
    os.environ["TTL_DAYS"] = "9"
    os.environ["LOCK_SWEEP_INTERVAL_SEC"] = "5"
    os.environ["LOCK_MAX_AGE_SEC"] = "99"

    cfg = Config.from_env()
    # Be robust across Windows/POSIX path styles
    assert cfg.app_home.as_posix().endswith("/x/app")
    assert cfg.data_root.as_posix().endswith("/x/data")
    assert cfg.public_root.as_posix().endswith("/x/work")
    assert cfg.log_dir.as_posix().endswith("/x/logs")
    assert cfg.docx2tex_home.as_posix().endswith("/x/docx2tex")
    assert cfg.catalog_file.as_posix().endswith("/x/catalog.xml")
    assert cfg.db_path.as_posix().endswith("/x/state.db")
    assert cfg.max_upload_bytes == 1234
    assert cfg.uvicorn_workers == 3
    assert cfg.ttl_days == 9
    assert cfg.lock_sweep_interval_sec == 5
    assert cfg.lock_max_age_sec == 99
