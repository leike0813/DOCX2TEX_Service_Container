"""Rewrite tabularray environments to classic tabular."""

from __future__ import annotations

import io
import re

from . import PreprocessorState, registry
from .helpers import find_balanced_brace


@registry.register("tabularray", description="Rewrite \\begin{tblr} tables into \\begin{tabular}.")
def rewrite_tblr(state: PreprocessorState) -> None:
    out = io.StringIO()
    i, n = 0, len(state.text)
    begin, end = r"\begin{tblr}", r"\end{tblr}"
    while i < n:
        j = state.text.find(begin, i)
        if j == -1:
            out.write(state.text[i:])
            break
        out.write(state.text[i:j])
        k = j + len(begin)
        while k < n and state.text[k].isspace():
            k += 1
        options = ""
        if k < n and state.text[k] == "{":
            opt_end = find_balanced_brace(state.text, k)
            if opt_end == -1:
                out.write(state.text[j:])
                break
            options = state.text[k + 1 : opt_end]
            k = opt_end + 1
        closing = state.text.find(end, k)
        if closing == -1:
            out.write(state.text[j:])
            break
        body = state.text[k:closing]
        columns = _parse_colspec(options) or ["l"] * _count_columns(body)
        want_h = bool(re.search(r"\bhlines\b", options))
        want_v = bool(re.search(r"\bvlines\b", options))
        tab_body = _inject_hlines(body) if want_h else body
        coldef = _build_coldef(columns, want_v)
        out.write(r"\begin{tabular}{" + coldef + "}\n")
        out.write(tab_body.strip() + "\n")
        out.write(r"\end{tabular}")
        i = closing + len(end)
        while i < n and state.text[i] in " \t\r\n":
            out.write(state.text[i])
            i += 1
    state.replace_text(out.getvalue())


def _parse_colspec(opt: str) -> list[str] | None:
    match = re.search(r"colspec\s*=\s*{", opt)
    if not match:
        return None
    start = match.end() - 1
    end = find_balanced_brace(opt, start)
    if end == -1:
        return None
    body = opt[start + 1 : end].replace("\n", " ").replace("\t", " ")
    tokens = re.findall(r"(X\[[^\]]*\]|[lcr])", body)
    cols: list[str] = []
    for token in tokens:
        if token.startswith("X["):
            if re.search(r"[,=]r[,}]?", token):
                cols.append("r")
            elif re.search(r"[,=]c[,}]?", token):
                cols.append("c")
            else:
                cols.append("l")
        elif token in ("l", "c", "r"):
            cols.append(token)
    return cols or None


def _count_columns(body: str) -> int:
    cleaned = re.sub(r"^(\\hline\s*)+", "", body.lstrip())
    match = re.search(r"^(.*?)(?<!\\)\\\\", cleaned, flags=re.S)
    first_row = match.group(1) if match else (cleaned.splitlines()[0] if cleaned.splitlines() else "")
    return max(1, len(re.findall(r"(?<!\\)&", first_row)) + 1)


def _inject_hlines(body: str) -> str:
    parts = re.split(r"(?<!\\)\\\\", body)
    out_lines: list[str] = []
    for segment in parts:
        segment = segment.rstrip()
        if not segment.strip():
            continue
        out_lines.append(segment + r"\\")
        if not re.search(r"\\hline\s*$", segment):
            out_lines.append(r"\hline")
    joined = "\n".join(out_lines).strip()
    if joined and not joined.startswith(r"\hline"):
        joined = r"\hline" + "\n" + joined
    if joined and not joined.endswith(r"\hline"):
        joined = joined + "\n" + r"\hline"
    return joined + "\n"


def _build_coldef(cols: list[str], vlines: bool) -> str:
    spec = "".join(cols) if cols else "l"
    return ("|" + "|".join(spec) + "|") if vlines else spec
