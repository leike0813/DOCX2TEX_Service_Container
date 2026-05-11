from __future__ import annotations

import os
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlparse

INTERNAL_DOCX_FILENAME = "input.docx"
INTERNAL_BASENAME = "input"
DEFAULT_DISPLAY_BASENAME = "document"


@dataclass(frozen=True)
class Docx2TexNameMapping:
    original_filename: str
    display_basename: str
    internal_filename: str = INTERNAL_DOCX_FILENAME
    internal_basename: str = INTERNAL_BASENAME

    @property
    def result_name(self) -> str:
        return f"{self.display_basename}.zip"


def name_mapping_from_upload(filename: str | None) -> Docx2TexNameMapping:
    original = _clean_original_filename(filename or "document.docx")
    return Docx2TexNameMapping(
        original_filename=original,
        display_basename=display_basename(original),
    )


def name_mapping_from_url(url: str) -> Docx2TexNameMapping:
    original = "document.docx"
    try:
        parsed = urlparse(url)
        candidate = unquote(Path(parsed.path).name)
        if candidate:
            original = candidate
    except Exception:
        pass
    original = _clean_original_filename(original)
    if not original.lower().endswith(".docx"):
        original = f"{original}.docx"
    return Docx2TexNameMapping(
        original_filename=original,
        display_basename=display_basename(original),
    )


def display_basename(filename: str | None) -> str:
    original = _clean_original_filename(filename or "")
    stem, _ = os.path.splitext(original)
    return _clean_path_component(stem, default=DEFAULT_DISPLAY_BASENAME)


def _clean_original_filename(filename: str) -> str:
    cleaned = _clean_path_component(filename, default="document.docx")
    return cleaned or "document.docx"


def _clean_path_component(value: str, *, default: str) -> str:
    # Preserve Unicode display text, but remove characters that can escape ZIP paths
    # or produce invalid filesystem components.
    value = value.replace("\\", "/").split("/")[-1]
    chars: list[str] = []
    for char in unicodedata.normalize("NFC", value):
        category = unicodedata.category(char)
        if category.startswith("C") or char in {"/", "\\"}:
            chars.append("_")
        else:
            chars.append(char)
    cleaned = "".join(chars).strip().strip(".")
    return cleaned or default
