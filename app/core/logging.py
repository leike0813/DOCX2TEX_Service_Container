from __future__ import annotations

import time
from pathlib import Path


def log_line(log_path: Path, msg: str) -> None:
    """Append a timestamped line to a log file (best-effort)."""
    try:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {msg}\n"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "ab") as lf:
            lf.write(line.encode("utf-8", errors="ignore"))
    except Exception:
        pass


def console(msg: str) -> None:
    """Print a timestamped message to stdout (best-effort)."""
    try:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts}] {msg}", flush=True)
    except Exception:
        pass


def log_exception(log_path: Path, prefix: str, exc: Exception) -> None:
    try:
        log_line(log_path, f"{prefix}: {exc}")
        console(f"{prefix}: {exc}")
    except Exception:
        pass

