"""Shared helper utilities for preprocessing plugins."""

from __future__ import annotations


def find_balanced_brace(text: str, start: int) -> int:
    if start < 0 or start >= len(text) or text[start] != "{":
        return -1
    depth = 0
    for idx in range(start, len(text)):
        char = text[idx]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return idx
    return -1


def find_balanced_bracket(text: str, start: int) -> int:
    if start < 0 or start >= len(text) or text[start] != "[":
        return -1
    depth = 0
    for idx in range(start, len(text)):
        char = text[idx]
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return idx
    return -1
