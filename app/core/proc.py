from __future__ import annotations

from pathlib import Path
from typing import Optional

import requests


def run_subprocess(cmd: list[str], cwd: Optional[Path] = None, env: Optional[dict] = None, timeout: int = 600) -> tuple[int, str, str]:
    import subprocess

    proc = subprocess.Popen(cmd, cwd=str(cwd) if cwd else None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    try:
        out, err = proc.communicate(timeout=timeout)
        return proc.returncode, out, err
    except subprocess.TimeoutExpired:
        proc.kill()
        out, err = proc.communicate()
        return 124, out, err


def download_to(path: Path, url: str):
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(r.content)

