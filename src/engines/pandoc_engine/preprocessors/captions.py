"""Cleanup caption-related LaTeX constructs."""

from __future__ import annotations

import io
import re

from . import PreprocessorState, registry
from .helpers import find_balanced_brace, find_balanced_bracket

CAPTION_CMD = r"\captionsetup"


@registry.register("captionsetup_cleanup", description="Simplify bicaption-specific \\captionsetup usage.")
def cleanup_captions(state: PreprocessorState) -> None:
    text = re.sub(r"^\s*\\usepackage\s*{bicaption}\s*\n?", "", state.text, flags=re.M)
    out = io.StringIO()
    i, n = 0, len(text)
    while i < n:
        j = text.find(CAPTION_CMD, i)
        if j == -1:
            out.write(text[i:])
            break
        out.write(text[i:j])
        k = j + len(CAPTION_CMD)
        while k < n and text[k].isspace():
            k += 1
        if k >= n or text[k] != "[":
            out.write(text[j])
            i = j + 1
            continue
        scope_end = find_balanced_bracket(text, k)
        if scope_end == -1:
            out.write(text[j:])
            break
        scope = text[k + 1 : scope_end].strip()
        k = scope_end + 1
        while k < n and text[k].isspace():
            k += 1
        mode = None
        if k < n and text[k] == "[":
            mode_end = find_balanced_bracket(text, k)
            if mode_end == -1:
                out.write(text[j:])
                break
            mode = text[k + 1 : mode_end].strip()
            k = mode_end + 1
        while k < n and text[k].isspace():
            k += 1
        if k >= n or text[k] != "{":
            out.write(text[j])
            i = j + 1
            continue
        body_end = find_balanced_brace(text, k)
        if body_end == -1:
            out.write(text[j:])
            break
        body = text[k + 1 : body_end]
        after = body_end + 1
        if mode == "bi-second":
            match = re.match(r"[ \t]*(?:%[^\n]*)?\n?", text[after:])
            eaten = match.end() if match else 0
            i = after + eaten
            continue
        if scope:
            out.write(r"\captionsetup[" + scope + "]{" + body + "}")
        else:
            out.write(r"\captionsetup{" + body + "}")
        i = after
    state.replace_text(out.getvalue())
