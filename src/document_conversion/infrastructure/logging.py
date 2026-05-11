from __future__ import annotations

import time
from pathlib import Path


def log_line(log_path: Path, message: str) -> None:
    try:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "ab") as handle:
            handle.write(f"[{timestamp}] {message}\n".encode("utf-8", errors="ignore"))
    except Exception:
        pass


def console(message: str) -> None:
    try:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}", flush=True)
    except Exception:
        pass


def log_exception(log_path: Path, prefix: str, exc: Exception) -> None:
    try:
        log_line(log_path, f"{prefix}: {exc}")
        console(f"{prefix}: {exc}")
    except Exception:
        pass
