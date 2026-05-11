"""Remove \\tsup wrappers around citation commands."""

from __future__ import annotations

import re

from . import PreprocessorState, registry


@registry.register("tsup_citation", description="Inline citation commands instead of \\tsup{\\cite...}.")
def unwrap_tsup_citations(state: PreprocessorState) -> None:
    state.replace_text(re.sub(r"\\tsup\s*{\s*(\\cite[^{}]*{[^{}]+})\s*}", r"\1", state.text))
