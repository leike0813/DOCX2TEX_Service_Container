from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from engines.pandoc_engine.config import TemplateDetector, TemplateRegistry
from engines.pandoc_engine.converter import PANDOC_PROFILES, PandocEngine
from engines.pandoc_engine.orchestrator import PipelineContext, PipelineOrchestrator
from engines.pandoc_engine.preprocessors import graphics as graphics_preprocessor
from engines.pandoc_engine.preprocessors import run_preprocessors
from engines.pandoc_engine.resources import (
    default_latex_to_docx_options,
    latex_to_docx_option_payload,
    reference_doc_path,
)


def test_template_detection_prefers_specific_class() -> None:
    templates_dir = Path("src/engines/pandoc_engine/assets/templates")
    registry = TemplateRegistry(templates_dir)
    detector = TemplateDetector(registry)
    tex_path = Path("tests/fixtures/elsarticle.tex")
    config = detector.guess(tex_path)
    assert config.name == "elsarticle"


def test_tabularx_preprocessor_rewrites_environment() -> None:
    text = (
        r"\begin{tabularx}{\linewidth}{|X|X[r]|c|}" "\n"
        r"\hline" "\n"
        r"a & b \\" "\n"
        r"\hline" "\n"
        r"\end{tabularx}"
    )
    processed, executed, _ = run_preprocessors(["tabularx"], text)
    assert executed == ["tabularx"]
    assert r"\begin{tabular}{|l|r|c|}" in processed
    assert "tabularx" not in processed


def test_reference_doc_is_materialized(tmp_path: Path) -> None:
    path = reference_doc_path("ctexbook", tmp_path)
    assert path.exists()
    assert path.suffix == ".docx"


def test_latex_to_docx_defaults_and_option_payload() -> None:
    defaults = default_latex_to_docx_options("latex_to_docx/pandoc-ctexbook")
    assert defaults["reference_doc_id"] == "ctexbook"
    assert defaults["top_level_division"] == "chapter"

    payload = latex_to_docx_option_payload()
    exec_filters = payload["exec_filters"]
    assert isinstance(exec_filters, list)
    assert any(item["id"] == "pandoc-tex-numbering" for item in exec_filters)

    csl = payload["csl"]
    assert isinstance(csl, list)
    assert any(item["id"] == "gb-t-7714-2015-numeric" for item in csl)


def test_orchestrator_builds_reference_doc_and_citation_args(tmp_path: Path) -> None:
    templates_dir = Path("src/engines/pandoc_engine/assets/templates")
    registry = TemplateRegistry(templates_dir)
    orchestrator = PipelineOrchestrator(registry)

    source = tmp_path / "main.tex"
    source.write_text(
        "\\documentclass{article}\\begin{document}Hello\\end{document}",
        encoding="utf-8",
    )
    output = tmp_path / "result.docx"
    bibliography = tmp_path / "refs.bib"
    bibliography.write_text("@article{a,title={T}}\n", encoding="utf-8")

    ctx = PipelineContext(
        source_path=source,
        output_path=output,
        workdir=tmp_path / "work",
        reference_doc=reference_doc_path("article-default", tmp_path),
        metadata_files=[Path("src/engines/pandoc_engine/assets/metadata/custom-meta.yaml")],
        lua_filters=[Path("src/engines/pandoc_engine/assets/filters/caption_colon_to_space.lua")],
        exec_filters=["pandoc-tex-numbering"],
        top_level_division="section",
        citeproc=True,
        csl=Path("src/engines/pandoc_engine/assets/csl/gb-t-7714-2015-numeric.csl"),
        bibliography_paths=[bibliography],
    )
    plan = orchestrator.build_plan(ctx)

    command = " ".join(plan.pandoc_command)
    assert "--reference-doc" in command
    assert "--metadata-file" in command
    assert "--lua-filter=" in command
    assert "--filter pandoc-tex-numbering" in command
    assert "--citeproc" in command
    assert "--csl" in command
    assert "--bibliography" in command


def test_bibliography_auto_discovery_and_workspace_guard(tmp_path: Path) -> None:
    engine = PandocEngine()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "one.bib").write_text("@book{a,title={A}}", encoding="utf-8")
    nested = workspace / "refs"
    nested.mkdir()
    (nested / "two.bib").write_text("@book{b,title={B}}", encoding="utf-8")

    discovered = engine._resolve_bibliography_paths(workspace, [], True)
    assert [item.name for item in discovered] == ["one.bib", "two.bib"]

    with pytest.raises(RuntimeError):
        engine._resolve_bibliography_paths(workspace, ["../escape.bib"], True)


def test_missing_exec_filter_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = PandocEngine()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    entry_tex = workspace / "main.tex"
    entry_tex.write_text(
        "\\documentclass{article}\\begin{document}Hi\\end{document}",
        encoding="utf-8",
    )
    runtime = SimpleNamespace(cfg=SimpleNamespace(data_root=tmp_path / "data"))
    profile = next(item for item in PANDOC_PROFILES if item.id == "latex_to_docx/pandoc-ctexart")

    monkeypatch.setattr(
        "engines.pandoc_engine.converter.available_exec_filter",
        lambda _item: False,
    )

    with pytest.raises(RuntimeError, match="Required executable filter is missing"):
        engine._resolve_latex_to_docx_options(runtime, workspace, profile, entry_tex, {})


def test_includegraphics_svg_is_rewritten_to_emf(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    source_dir = workspace / "chapters"
    source_dir.mkdir()
    svg = workspace / "assets" / "plot.svg"
    svg.parent.mkdir()
    svg.write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")

    def fake_run(
        command: list[str],
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        target = Path(command[command.index("--export-filename") + 1])
        target.write_bytes(b"EMF")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(graphics_preprocessor.subprocess, "run", fake_run)

    processed, executed, metadata = run_preprocessors(
        ["includegraphics_assets"],
        r"\includegraphics{../assets/plot.svg}",
        {
            "source_dir": source_dir,
            "workspace_root": workspace,
            "generated_images_dir": tmp_path / "generated-images",
        },
    )

    assert executed == ["includegraphics_assets"]
    assert ".emf" in processed
    conversions = metadata["image_conversions"]
    assert isinstance(conversions, list)
    assert conversions[0]["output_format"] == "emf"


def test_includegraphics_pdf_falls_back_to_png(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    pdf = workspace / "figure.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    calls: list[list[str]] = []

    def fake_run(
        command: list[str],
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        target = Path(command[command.index("--export-filename") + 1])
        export_type = command[command.index("--export-type") + 1]
        if export_type == "emf":
            raise subprocess.CalledProcessError(1, command, stderr="emf failed")
        target.write_bytes(b"PNG")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(graphics_preprocessor.subprocess, "run", fake_run)

    processed, _, metadata = run_preprocessors(
        ["includegraphics_assets"],
        r"\includegraphics{figure.pdf}",
        {
            "source_dir": workspace,
            "workspace_root": workspace,
            "generated_images_dir": tmp_path / "generated-images",
        },
    )

    assert ".png" in processed
    fallbacks = metadata["fallbacks"]
    assert isinstance(fallbacks, list)
    assert fallbacks[0]["fallback_format"] == "png"
    assert any("--export-dpi" in command for command in calls)


def test_includegraphics_svg_failure_keeps_original_asset_as_resolved_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    svg = workspace / "diagram.svg"
    svg.write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")

    def fake_run(
        command: list[str],
        check: bool,
        capture_output: bool,
        text: bool,
    ) -> subprocess.CompletedProcess[str]:
        raise subprocess.CalledProcessError(1, command, stderr="emf failed")

    monkeypatch.setattr(graphics_preprocessor.subprocess, "run", fake_run)

    processed, _, metadata = run_preprocessors(
        ["includegraphics_assets"],
        r"\includegraphics{diagram.svg}",
        {
            "source_dir": workspace,
            "workspace_root": workspace,
            "generated_images_dir": tmp_path / "generated-images",
        },
    )

    assert svg.resolve().as_posix() in processed
    failures = metadata["image_conversion_failures"]
    assert isinstance(failures, list)
    assert failures[0]["source"] == str(svg.resolve())
