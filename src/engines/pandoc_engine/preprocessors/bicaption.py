"""Convert \\bicaption blocks into caption + italicised translation."""

from __future__ import annotations

import io
import re

from . import PreprocessorState, registry
from .helpers import find_balanced_brace

LABEL_FOLLOW_RE = re.compile(r"(?:[ \t\r\n]|%[^\n]*\n)*(\\label\s*{\s*([^{}]+)\s*})?")


@registry.register("bicaption", description="Expand \\bicaption into caption + italicised translation.")
def convert_bicaption(state: PreprocessorState) -> None:
    out = io.StringIO()
    i, n = 0, len(state.text)
    cmd = r"\bicaption"
    while i < n:
        j = state.text.find(cmd, i)
        if j == -1:
            out.write(state.text[i:])
            break
        out.write(state.text[i:j])
        k = j + len(cmd)
        while k < n and state.text[k].isspace():
            k += 1
        if k >= n or state.text[k] != "{":
            out.write(cmd)
            i = k
            continue
        cn_end = find_balanced_brace(state.text, k)
        if cn_end == -1:
            out.write(state.text[j:])
            break
        cn = state.text[k + 1 : cn_end].strip()
        k = cn_end + 1
        while k < n and state.text[k].isspace():
            k += 1
        if k >= n or state.text[k] != "{":
            out.write(r"\caption{" + cn + "}\n")
            i = k
            continue
        en_end = find_balanced_brace(state.text, k)
        if en_end == -1:
            out.write(r"\caption{" + cn + "}\n")
            i = k
            continue
        en = state.text[k + 1 : en_end].strip()
        k = en_end + 1
        label_match = LABEL_FOLLOW_RE.match(state.text, k)
        label_key = label_match.group(2) if label_match else None
        after = label_match.end() if label_match else k
        if label_key:
            out.write(r"\caption{" + cn + r"}" + r"\label{" + label_key + r"}" + "\n")
            out.write(r"\textit{" + r"\cref{" + label_key + r"} " + en + r"}" + "\n")
        else:
            out.write(r"\caption{" + cn + r"}" + "\n")
            out.write(r"\textit{" + en + r"}" + "\n")
        i = after
    state.replace_text(out.getvalue())
