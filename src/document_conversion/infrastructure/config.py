from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from engines.docx2tex_engine.assets import (
    render_catalog,
    resolve_catalog_template,
    resolve_docx2tex_home,
)

from .storage import is_mountpoint

_CONFIG_SINGLETON: Config | None = None
_REPO_ROOT = Path(__file__).resolve().parents[3]
_LOCAL_ROOT = _REPO_ROOT / ".local"


def _env_path(name: str, default: Path) -> Path:
    raw = os.environ.get(name, "").strip()
    return Path(raw).resolve() if raw else default.resolve()


def _parse_int(value: str | None, default: int) -> int:
    if value is None or not str(value).strip():
        return default
    try:
        return int(str(value).strip())
    except ValueError:
        return default


@dataclass(frozen=True)
class Config:
    app_home: Path
    data_root: Path
    public_root: Path
    log_dir: Path
    docx2tex_home: Path
    catalog_file: Path
    db_path: Path
    max_upload_bytes: int
    uvicorn_workers: int
    ttl_days: int | None
    lock_sweep_interval_sec: int
    lock_max_age_sec: int

    @staticmethod
    def from_env() -> Config:
        app_home = _env_path("APP_HOME", _REPO_ROOT)
        data_root = _env_path("DATA_ROOT", _LOCAL_ROOT / "data")
        public_root = _env_path("WORK_ROOT", _LOCAL_ROOT / "work")
        log_dir = _env_path("LOG_DIR", _LOCAL_ROOT / "logs")
        runtime_root = data_root.parent / "runtime"
        default_docx2tex_home = resolve_docx2tex_home()
        docx2tex_home = _env_path("DOCX2TEX_HOME", default_docx2tex_home)
        if os.environ.get("XML_CATALOG_FILES", "").strip():
            catalog_file = _env_path("XML_CATALOG_FILES", resolve_catalog_template())
        else:
            catalog_file = render_catalog(
                resolve_catalog_template(),
                docx2tex_home,
                runtime_root / "xmlcatalog" / "catalog.xml",
            )
        db_path = Path(os.environ.get("STATE_DB", str(data_root / "state.db"))).resolve()

        max_upload_raw = os.environ.get("MAX_UPLOAD_BYTES", "0")
        try:
            max_upload_bytes = int(max_upload_raw) if str(max_upload_raw).strip() else 0
        except ValueError:
            max_upload_bytes = 0

        uvicorn_workers = _parse_int(os.environ.get("UVICORN_WORKERS"), 2)

        ttl_raw = os.environ.get("TTL_DAYS", "").strip()
        if ttl_raw:
            try:
                ttl_days: int | None = int(ttl_raw)
            except ValueError:
                ttl_days = 7
        else:
            ttl_days = None if is_mountpoint(data_root) else 7

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
            lock_sweep_interval_sec=_parse_int(
                os.environ.get("LOCK_SWEEP_INTERVAL_SEC"),
                120,
            ),
            lock_max_age_sec=_parse_int(
                os.environ.get("LOCK_MAX_AGE_SEC"),
                1800,
            ),
        )


def get_config() -> Config:
    global _CONFIG_SINGLETON
    if _CONFIG_SINGLETON is None:
        _CONFIG_SINGLETON = Config.from_env()
    return _CONFIG_SINGLETON


def reset_config() -> None:
    global _CONFIG_SINGLETON
    _CONFIG_SINGLETON = None
