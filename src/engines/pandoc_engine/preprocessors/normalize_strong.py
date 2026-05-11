"""Normalize non-standard strong text commands."""

from __future__ import annotations

import re

from . import PreprocessorState, registry


@registry.register("normalize_strong", description="Normalize \\strong to \\textbf.")
def normalize_strong(state: PreprocessorState) -> None:
    state.replace_text(re.sub(r"\\strong\s*{", r"\\textbf{", state.text))
