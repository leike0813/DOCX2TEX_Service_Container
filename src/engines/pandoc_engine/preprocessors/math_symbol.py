"""Normalize inline math single-symbol segments."""

from __future__ import annotations

import re

from . import PreprocessorState, registry

INLINE_MATH_RE = re.compile(r"(?<!\$)\$(.+?)(?<!\$)\$(?!\$)", flags=re.S)
GREEK = {"alpha": "α", "beta": "β", "gamma": "γ", "pi": "π", "Phi": "Φ", "Omega": "Ω"}


@registry.register("math_symbol", description="Wrap one-letter inline math segments with \\emph{}.")
def emphasize_single_symbols(state: PreprocessorState) -> None:
    def convert(match: re.Match[str]) -> str:
        inside = match.group(1).strip()
        bm = re.match(r"^\\(?:bm|boldsymbol)\s*{\s*(.+?)\s*}$", inside)
        if bm:
            inside = bm.group(1).strip()
        greek = re.match(r"^\\([A-Za-z]+)$", inside)
        if greek and greek.group(1) in GREEK:
            return r"\emph{" + GREEK[greek.group(1)] + "}"
        if re.match(r"^[A-Za-z]$", inside):
            return r"\emph{" + inside + "}"
        return match.group(0)

    state.replace_text(INLINE_MATH_RE.sub(convert, state.text))
