from __future__ import annotations

from pathlib import Path
from typing import Any

from .storage import atomic_write_json

TASK_METADATA_NAME = "task-metadata.json"


def write_task_metadata(work_dir: Path, payload: dict[str, Any]) -> None:
    atomic_write_json(work_dir / TASK_METADATA_NAME, payload)


def read_task_metadata(work_dir: Path) -> dict[str, Any]:
    path = work_dir / TASK_METADATA_NAME
    if not path.exists():
        return {}
    import json

    return json.loads(path.read_text(encoding="utf-8"))
