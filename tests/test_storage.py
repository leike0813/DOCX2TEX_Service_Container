from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from app.core.storage import atomic_write_json, compute_sha256, safe_name


def test_safe_name_basic():
    assert safe_name("abc.txt") == "abc.txt"
    assert safe_name("a b@c.txt") == "a_b_c.txt"
    assert safe_name("你好.txt").startswith("__") or safe_name("你好.txt").endswith(".txt")


def test_atomic_write_json_and_hash():
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "data.json"
        data = {"x": 1, "y": "测试"}
        atomic_write_json(p, data)
        # File exists and valid JSON
        loaded = json.loads(p.read_text(encoding="utf-8"))
        assert loaded == data
        # Hash is stable and 64 hex chars
        h = compute_sha256(p)
        assert isinstance(h, str) and len(h) == 64 and all(c in "0123456789abcdef" for c in h)

