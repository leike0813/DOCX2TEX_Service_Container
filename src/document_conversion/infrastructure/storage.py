from __future__ import annotations

import json
from pathlib import Path


def to_file_uri(path: Path) -> str:
    return path.resolve().as_uri()


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(data)


def atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)


def safe_name(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in (".", "_", "-", "+") else "_" for ch in name)


def is_mountpoint(path: Path) -> bool:
    try:
        target = str(path.resolve())
        with open("/proc/self/mountinfo", "r", encoding="utf-8", errors="ignore") as handle:
            for line in handle:
                parts = line.strip().split()
                if len(parts) >= 5 and parts[4] == target:
                    return True
    except Exception:
        pass
    return False


def compute_sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
