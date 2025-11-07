from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Config
from app.core.db import Database
from app.core.cache import CacheStore, LockManager
from app.core.tasks import TaskStore


@dataclass
class AppContext:
    config: Config
    db: Database
    cache: CacheStore
    locks: LockManager
    tasks: TaskStore

