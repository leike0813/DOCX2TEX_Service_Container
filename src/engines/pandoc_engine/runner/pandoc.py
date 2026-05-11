"""Pandoc invocation helper."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Sequence


class PandocRunner:
    def __init__(self, binary: str = "pandoc"):
        self.binary = binary

    def build_command(
        self,
        source_tex: Path,
        output_docx: Path,
        spec: dict[str, object],
        extra_args: Sequence[str] | None = None,
    ) -> list[str]:
        args: list[str] = [self.binary, str(source_tex), "-o", str(output_docx)]
        reader = spec.get("reader")
        writer = spec.get("writer")
        if reader:
            args.extend(["-f", str(reader)])
        if writer:
            args.extend(["-t", str(writer)])
        raw_args = spec.get("args", [])
        if isinstance(raw_args, list):
            args.extend(str(item) for item in raw_args)
        reference_doc = spec.get("reference_doc")
        if reference_doc and Path(str(reference_doc)).exists():
            args.extend(["--reference-doc", str(reference_doc)])
        if extra_args:
            args.extend(extra_args)
        return args

    def run(self, command: Sequence[str], dry_run: bool = False) -> None:
        if dry_run:
            return
        subprocess.run(list(command), check=True)
