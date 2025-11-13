from __future__ import annotations

import logging
import os
import re
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Iterable

import jieba

from .storage import safe_name

jieba.setLogLevel(logging.ERROR)
INVALID_CHARS = re.compile(r"[^A-Za-z0-9]+")
MAX_LENGTH = 40
MAX_TAIL_WORDS = 4


@lru_cache(maxsize=1)
def _load_cedict(path: Path | None = None) -> dict[str, str]:
    if path is None:
        path = Path(__file__).resolve().parents[2] / "resources" / "cedict_ts.u8"
    mapping: dict[str, str] = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("/", 1)
                if len(parts) < 2:
                    continue
                header, definitions = parts
                words = header.split()
                if not words:
                    continue
                trad = words[0]
                simp = words[1] if len(words) > 1 else trad
                defs = definitions.strip().strip("/")
                first_def = defs.split("/")[0] if defs else "term"
                term = first_def.split(";")[0]
                mapping[trad] = term
                mapping[simp] = term
    except Exception:
        pass
    return mapping


def _translate_with_dictionary(text: str, dictionary: dict[str, str]) -> list[str]:
    words: list[str] = []
    for term in jieba.lcut(text):
        term = term.strip()
        if not term:
            continue
        candidate = dictionary.get(term)
        if candidate:
            parts = re.findall(r"[A-Za-z0-9]+", candidate)
            words.extend(parts)
        elif term.isascii() and term.isalnum():
            words.append(term)
        elif len(term) < 3:
            words.append(term)
        else:
            pinyin = "".join(_pinyin_transliteration(term))
            if pinyin:
                words.append(pinyin)
    return words


def _pinyin_transliteration(text: str) -> Iterable[str]:
    try:
        from pypinyin import lazy_pinyin

        return lazy_pinyin(text, strict=False)
    except ImportError:
        return ()


def _limit_length(candidate: str) -> str:
    if len(candidate) <= MAX_LENGTH:
        return candidate
    parts = [p for p in candidate.split("-") if p]
    if len(parts) <= MAX_TAIL_WORDS:
        return candidate[:MAX_LENGTH]
    head = "-".join(parts[: max(1, len(parts) - MAX_TAIL_WORDS)])
    tail = "-".join(parts[-MAX_TAIL_WORDS :])
    truncated = f"{head}-{tail}"
    return truncated[:MAX_LENGTH]


def _is_ascii(s: str) -> bool:
    return all(ord(ch) < 128 for ch in s)


def sanitize_filename(name: str, default: str = "file") -> str:
    if not name:
        return default
    base, ext = os.path.splitext(name)
    ascii_candidate = safe_name(base)
    if _is_ascii(base) and len(base) <= MAX_LENGTH:
        return f"{ascii_candidate}{ext}"
    dictionary = _load_cedict()
    translated_words = _translate_with_dictionary(base, dictionary) or []
    if not translated_words:
        normalized = unicodedata.normalize("NFKD", base)
        translated_words = [
            ch for ch in normalized if unicodedata.category(ch) != "Mn"
        ]
    candidate = "-".join(filter(None, translated_words))
    if not candidate:
        candidate = ascii_candidate or default
    candidate = _limit_length(candidate)
    sanitized = safe_name(candidate)
    sanitized = "".join(ch for ch in sanitized if _is_ascii(ch) or ch in ".-_+")
    if not sanitized:
        sanitized = default
    return f"{sanitized}{ext}"
