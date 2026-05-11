"""Rewrite tabularx environments so Pandoc sees classic tabular blocks."""

from __future__ import annotations

import io
import re

from . import PreprocessorState, registry
from .helpers import find_balanced_brace, find_balanced_bracket

_X_PATTERN = re.compile(r"X(\[[^\]]*\])?")


@registry.register("tabularx", description="Rewrite \\begin{tabularx} tables into \\begin{tabular}.")
def rewrite_tabularx(state: PreprocessorState) -> None:
    out = io.StringIO()
    i, n = 0, len(state.text)
    begin, end = r"\begin{tabularx}", r"\end{tabularx}"
    while i < n:
        j = state.text.find(begin, i)
        if j == -1:
            out.write(state.text[i:])
            break
        out.write(state.text[i:j])
        k = j + len(begin)
        while k < n and state.text[k].isspace():
            k += 1
        if k < n and state.text[k] == "[":
            opt_end = find_balanced_bracket(state.text, k)
            if opt_end == -1:
                out.write(state.text[j:])
                break
            k = opt_end + 1
            while k < n and state.text[k].isspace():
                k += 1
        if k >= n or state.text[k] != "{":
            out.write(state.text[j : j + len(begin)])
            i = j + len(begin)
            continue
        width_end = find_balanced_brace(state.text, k)
        if width_end == -1:
            out.write(state.text[j:])
            break
        k = width_end + 1
        while k < n and state.text[k].isspace():
            k += 1
        if k >= n or state.text[k] != "{":
            out.write(state.text[j:])
            break
        col_end = find_balanced_brace(state.text, k)
        if col_end == -1:
            out.write(state.text[j:])
            break
        colspec = state.text[k + 1 : col_end]
        k = col_end + 1
        closing = state.text.find(end, k)
        if closing == -1:
            out.write(state.text[j:])
            break
        body = state.text[k:closing].strip()
        rewritten_spec = _X_PATTERN.sub(_replace_column, colspec) or "l"
        out.write(r"\begin{tabular}{" + rewritten_spec + "}\n")
        if body:
            out.write(body + "\n")
        out.write(r"\end{tabular}")
        i = closing + len(end)
        while i < n and state.text[i] in " \t\r\n":
            out.write(state.text[i])
            i += 1
    state.replace_text(out.getvalue())


def _replace_column(match: re.Match[str]) -> str:
    option = match.group(1)
    if option:
        body = option[1:-1]
        if re.search(r"\br\b", body):
            return "r"
        if re.search(r"\bc\b", body):
            return "c"
        if re.search(r"\bl\b", body):
            return "l"
    return "l"
