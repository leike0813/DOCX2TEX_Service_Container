from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def to_file_uri(p: Path) -> str:
    return p.resolve().as_uri()


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


def atomic_write_json(path: Path, data: dict) -> None:
    """Write JSON atomically to the given path.

    Creates the parent directory, writes to a temp file in the same directory,
    then renames the temp file to the target.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    s = json.dumps(data, ensure_ascii=False, indent=2)
    tmp.write_text(s, encoding="utf-8")
    tmp.replace(path)


def safe_name(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in (".", "_", "-", "+") else "_" for ch in name)


def is_mountpoint(path: Path) -> bool:
    """Detect if a path is a mountpoint (best-effort).

    Uses /proc/self/mountinfo when available; otherwise returns False.
    """
    try:
        target = str(path.resolve())
        with open("/proc/self/mountinfo", "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 5 and parts[4] == target:
                    return True
    except Exception:
        pass
    return False


def compute_sha256(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

