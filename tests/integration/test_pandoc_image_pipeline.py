from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from engines.pandoc_engine.preprocessors import run_preprocessors


@pytest.mark.skipif(shutil.which("inkscape") is None, reason="inkscape is required")
def test_real_svg_is_converted_to_emf(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    svg = workspace / "plot.svg"
    svg.write_text(
        """<svg xmlns="http://www.w3.org/2000/svg" width="100" height="40">
<rect x="0" y="0" width="100" height="40" fill="#ffffff" stroke="#000000"/>
<text x="10" y="25" font-size="14">plot</text>
</svg>""",
        encoding="utf-8",
    )

    processed, executed, metadata = run_preprocessors(
        ["includegraphics_assets"],
        r"\includegraphics{plot.svg}",
        {
            "source_dir": workspace,
            "workspace_root": workspace,
            "generated_images_dir": tmp_path / "generated-images",
        },
    )

    assert executed == ["includegraphics_assets"]
    assert ".emf" in processed
    generated = metadata["generated_image_files"]
    assert isinstance(generated, list)
    assert generated
    generated_path = generated[0]
    assert isinstance(generated_path, Path)
    assert generated_path.exists()
    assert generated_path.suffix == ".emf"
