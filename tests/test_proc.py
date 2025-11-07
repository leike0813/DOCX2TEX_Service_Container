from __future__ import annotations

import sys

from app.core.proc import run_subprocess


def test_run_subprocess_python_ok():
    rc, out, err = run_subprocess([sys.executable, "-c", "print('OK')"], timeout=10)
    assert rc == 0
    assert "OK" in (out or "")

