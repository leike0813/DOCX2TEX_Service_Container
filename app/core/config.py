from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


def _parse_int(val: str | None, default: int) -> int:
    if val is None or str(val).strip() == "":
        return default
    try:
        return int(str(val).strip())
    except ValueError:
        return default


@dataclass(frozen=True)
class Config:
    """Centralized configuration derived from environment variables.

    This mirrors the existing environment usage in server.py while providing
    a typed, importable configuration object for other modules.
    """

    app_home: Path
    data_root: Path
    public_root: Path
    log_dir: Path
    docx2tex_home: Path
    catalog_file: Path
    db_path: Path

    max_upload_bytes: int
    uvicorn_workers: int
    ttl_days: Optional[int]
    lock_sweep_interval_sec: int
    lock_max_age_sec: int

    @staticmethod
    def from_env() -> "Config":
        from .storage import is_mountpoint  # local import to avoid cycles

        app_home = Path(os.environ.get("APP_HOME", "/app")).resolve()
        data_root = Path(os.environ.get("DATA_ROOT", "/data")).resolve()
        public_root = Path(os.environ.get("WORK_ROOT", "/work")).resolve()
        log_dir = Path(os.environ.get("LOG_DIR", "/var/log/docx2tex")).resolve()
        docx2tex_home = Path(os.environ.get("DOCX2TEX_HOME", "/opt/docx2tex")).resolve()
        catalog_file = Path(os.environ.get("XML_CATALOG_FILES", "/opt/catalog/catalog.xml")).resolve()
        db_path = Path(os.environ.get("STATE_DB", str(data_root / "state.db"))).resolve()

        max_upload_raw = os.environ.get("MAX_UPLOAD_BYTES", "0")
        try:
            max_upload_bytes = int(max_upload_raw) if str(max_upload_raw).strip() else 0
        except ValueError:
            max_upload_bytes = 0

        uvicorn_workers = _parse_int(os.environ.get("UVICORN_WORKERS"), 2)

        # TTL_DAYS semantics: if not set and data_root is a mountpoint, do not clean (None)
        ttl_raw = os.environ.get("TTL_DAYS", "").strip()
        if ttl_raw:
            try:
                ttl_days: Optional[int] = int(ttl_raw)
            except ValueError:
                ttl_days = 7
        else:
            ttl_days = None if is_mountpoint(data_root) else 7

        lock_sweep_interval_sec = _parse_int(os.environ.get("LOCK_SWEEP_INTERVAL_SEC"), 120)
        lock_max_age_sec = _parse_int(os.environ.get("LOCK_MAX_AGE_SEC"), 1800)

        return Config(
            app_home=app_home,
            data_root=data_root,
            public_root=public_root,
            log_dir=log_dir,
            docx2tex_home=docx2tex_home,
            catalog_file=catalog_file,
            db_path=db_path,
            max_upload_bytes=max_upload_bytes,
            uvicorn_workers=uvicorn_workers,
            ttl_days=ttl_days,
            lock_sweep_interval_sec=lock_sweep_interval_sec,
            lock_max_age_sec=lock_max_age_sec,
        )

    def as_dict(self) -> dict:
        return {
            "app_home": str(self.app_home),
            "data_root": str(self.data_root),
            "public_root": str(self.public_root),
            "log_dir": str(self.log_dir),
            "docx2tex_home": str(self.docx2tex_home),
            "catalog_file": str(self.catalog_file),
            "db_path": str(self.db_path),
            "max_upload_bytes": self.max_upload_bytes,
            "uvicorn_workers": self.uvicorn_workers,
            "ttl_days": self.ttl_days,
            "lock_sweep_interval_sec": self.lock_sweep_interval_sec,
            "lock_max_age_sec": self.lock_max_age_sec,
        }


def get_config() -> Config:
    """Return a process-wide singleton Config instance."""
    global _CONFIG_SINGLETON
    try:
        cfg = _CONFIG_SINGLETON  # type: ignore[name-defined]
    except NameError:
        _CONFIG_SINGLETON = Config.from_env()  # type: ignore[assignment]
        cfg = _CONFIG_SINGLETON
    return cfg  # type: ignore[return-value]

