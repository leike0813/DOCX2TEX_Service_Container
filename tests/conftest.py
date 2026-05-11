from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import pytest

from document_conversion.infrastructure import runtime as runtime_module
from document_conversion.infrastructure.config import reset_config
from engines.docx2tex_engine.assets import resolve_docx2tex_home

filename_results: List[Tuple[str, str, str]] = []


@pytest.fixture(scope="module")
def report_results() -> List[Tuple[str, str, str]]:
    filename_results.clear()
    yield filename_results


@pytest.fixture
def isolated_platform_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setenv("DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("WORK_ROOT", str(tmp_path / "work"))
    monkeypatch.setenv("LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("DOCX2TEX_HOME", str(resolve_docx2tex_home()))
    monkeypatch.delenv("XML_CATALOG_FILES", raising=False)
    return tmp_path


@pytest.fixture(autouse=True)
def reset_runtime_singletons():
    reset_config()
    runtime_module._CONTEXT = None
    yield
    reset_config()
    runtime_module._CONTEXT = None


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    if not filename_results:
        return
    terminalreporter.write_sep("-", "filename handling results")
    for title, original, sanitized in filename_results:
        terminalreporter.write_line(f"{title}: {original} -> {sanitized}")
