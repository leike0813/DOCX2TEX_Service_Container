from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import FastAPI

from app.core.config import get_config
from app.core.db import Database
from app.core.cache import CacheStore, LockManager
from app.core.cleanup import start_cleanup_loop
from app.api.routes import router as api_router


_CFG = get_config()
_DB_CORE = Database(_CFG.db_path)
_CACHE_CORE = CacheStore(_DB_CORE, _CFG.data_root)
_LOCKS_CORE = LockManager(_DB_CORE)


app = FastAPI(title="docx2tex-service")
app.include_router(api_router)


@app.on_event("startup")
def on_startup():
    # Ensure dirs (DATA_ROOT private; PUBLIC_ROOT is user-visible)
    _CFG.data_root.mkdir(parents=True, exist_ok=True)
    _CFG.public_root.mkdir(parents=True, exist_ok=True)
    _CFG.log_dir.mkdir(parents=True, exist_ok=True)
    _DB_CORE.init_schema()

    # Unified TTL (days) for tasks and caches
    retention: Optional[int] = _CFG.ttl_days
    start_cleanup_loop(_CFG, _DB_CORE, _CACHE_CORE, retention, retention)

    # Start lock sweeper
    _LOCKS_CORE.start_sweeper(_CFG.lock_sweep_interval_sec, _CFG.lock_max_age_sec)
