from __future__ import annotations

import importlib
import logging
import os
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from document_conversion.infrastructure.storage import safe_name

_jieba_module: object | None
try:
    _jieba_module = importlib.import_module("jieba")
except ModuleNotFoundError:
    _jieba_module = None

if _jieba_module is not None:
    _jieba_module.setLogLevel(logging.ERROR)  # type: ignore[attr-defined]

MAX_LENGTH = 40
MAX_TAIL_WORDS = 4


@lru_cache(maxsize=1)
def _load_cedict(path: Path | None = None) -> dict[str, str]:
    if path is None:
        path = Path(__file__).resolve().parents[3] / "resources" / "cedict_ts.u8"
    mapping: dict[str, str] = {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                header, _, definitions = line.partition("/")
                if not definitions:
                    continue
                words = header.split()
                if not words:
                    continue
                trad = words[0]
                simp = words[1] if len(words) > 1 else trad
                first_def = definitions.strip("/").split("/")[0] or "term"
                term = first_def.split(";")[0]
                mapping[trad] = term
                mapping[simp] = term
    except Exception:
        pass
    return mapping


def _segment_text(text: str) -> Iterable[str]:
    if _jieba_module is None:
        return list(text)
    return _jieba_module.lcut(text)  # type: ignore[attr-defined]


def _pinyin_transliteration(text: str) -> Iterable[str]:
    try:
        module = importlib.import_module("pypinyin")
        return module.lazy_pinyin(text, strict=False)  # type: ignore[attr-defined]
    except ModuleNotFoundError:
        return ()


def _translate_with_dictionary(text: str, dictionary: dict[str, str]) -> list[str]:
    words: list[str] = []
    for term in _segment_text(text):
        term = term.strip()
        if not term:
            continue
        candidate = dictionary.get(term)
        if candidate:
            words.extend(re.findall(r"[A-Za-z0-9]+", candidate))
        elif term.isascii() and term.isalnum():
            words.append(term)
        elif len(term) < 3:
            words.append(term)
        else:
            pinyin = "".join(_pinyin_transliteration(term))
            if pinyin:
                words.append(pinyin)
    return words


def _limit_length(candidate: str) -> str:
    if len(candidate) <= MAX_LENGTH:
        return candidate
    parts = [part for part in candidate.split("-") if part]
    if len(parts) <= MAX_TAIL_WORDS:
        return candidate[:MAX_LENGTH]
    head = "-".join(parts[: max(1, len(parts) - MAX_TAIL_WORDS)])
    tail = "-".join(parts[-MAX_TAIL_WORDS:])
    return f"{head}-{tail}"[:MAX_LENGTH]


def _is_ascii(text: str) -> bool:
    return all(ord(ch) < 128 for ch in text)


def sanitize_filename(name: str, default: str = "file") -> str:
    if not name:
        return default
    base, ext = os.path.splitext(name)
    ascii_candidate = safe_name(base)
    if _is_ascii(base) and len(base) <= MAX_LENGTH:
        return f"{ascii_candidate}{ext}"
    translated_words = _translate_with_dictionary(base, _load_cedict()) or []
    if not translated_words:
        normalized = unicodedata.normalize("NFKD", base)
        translated_words = [char for char in normalized if unicodedata.category(char) != "Mn"]
    candidate = "-".join(filter(None, translated_words)) or ascii_candidate or default
    sanitized = safe_name(_limit_length(candidate))
    sanitized = "".join(ch for ch in sanitized if _is_ascii(ch) or ch in ".-_+")
    return f"{(sanitized or default)}{ext}"
