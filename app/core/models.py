from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel


class JobState(BaseModel):
    task_id: str
    state: str
    err_msg: str = ""
    start_time: float
    end_time: Optional[float] = None
    debug: bool = False
    img_post_proc: bool = True
    work_dir: str
    sha256: Optional[str] = None


class CacheEntry(BaseModel):
    cache_key: str
    basename: str
    available: int = 1
    created: Optional[float] = None
    last_access: Optional[float] = None


class LockEntry(BaseModel):
    cache_key: str
    builder: Optional[str] = None
    started: Optional[float] = None

