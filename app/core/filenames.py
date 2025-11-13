from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path

from .storage import safe_name

INVALID_CHARS = re.compile(r"[^A-Za-z0-9]+")

def sanitize_filename(name: str, default: str = "file") -> str:
    if not name:
        return default
    base, ext = os.path.splitext(name)
    normalized = unicodedata.normalize("NFKD", base)
    ascii_only = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    ascii_only = INVALID_CHARS.sub("-", ascii_only)
    ascii_only = ascii_only.strip("-")
    if not ascii_only:
        ascii_only = default
    sanitized = f"{ascii_only}{ext}" if ext else ascii_only
    return safe_name(sanitized)
