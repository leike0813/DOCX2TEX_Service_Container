from __future__ import annotations

from pathlib import Path

import requests


def run_subprocess(
    cmd: list[str],
    cwd: Path | None = None,
    env: dict | None = None,
    timeout: int = 600,
) -> tuple[int, str, str]:
    import subprocess

    process = subprocess.Popen(
        cmd,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    try:
        stdout, stderr = process.communicate(timeout=timeout)
        return process.returncode, stdout, stderr
    except subprocess.TimeoutExpired:
        process.kill()
        stdout, stderr = process.communicate()
        return 124, stdout, stderr


def download_to(path: Path, url: str) -> None:
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(response.content)
