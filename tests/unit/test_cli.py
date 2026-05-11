from __future__ import annotations

import os
import subprocess
from pathlib import Path
from types import SimpleNamespace

import document_conversion.interfaces.cli as cli


def test_check_system_fails_when_pandoc_tex_numbering_is_missing(
    monkeypatch,
    tmp_path: Path,
) -> None:
    docx2tex_home = tmp_path / "docx2tex"
    docx2tex_home.mkdir()
    catalog_file = tmp_path / "catalog.xml"
    catalog_file.write_text("<catalog/>", encoding="utf-8")
    cfg = SimpleNamespace(docx2tex_home=docx2tex_home, catalog_file=catalog_file)

    def fake_which(name: str) -> str | None:
        available = {
            "java": "/usr/bin/java",
            "inkscape": "/usr/bin/inkscape",
            "pandoc": "/usr/bin/pandoc",
        }
        return available.get(name)

    monkeypatch.setattr(cli, "get_config", lambda: cfg)
    monkeypatch.setattr(cli.shutil, "which", fake_which)

    assert cli.check_system() == 1


def test_check_system_succeeds_when_required_binaries_exist(
    monkeypatch,
    tmp_path: Path,
) -> None:
    docx2tex_home = tmp_path / "docx2tex"
    docx2tex_home.mkdir()
    catalog_file = tmp_path / "catalog.xml"
    catalog_file.write_text("<catalog/>", encoding="utf-8")
    cfg = SimpleNamespace(docx2tex_home=docx2tex_home, catalog_file=catalog_file)

    def fake_which(name: str) -> str | None:
        available = {
            "java": "/usr/bin/java",
            "inkscape": "/usr/bin/inkscape",
            "pandoc": "/usr/bin/pandoc",
            "pandoc-tex-numbering": "/usr/bin/pandoc-tex-numbering",
        }
        return available.get(name)

    monkeypatch.setattr(cli, "get_config", lambda: cfg)
    monkeypatch.setattr(cli.shutil, "which", fake_which)

    assert cli.check_system() == 0


def test_entrypoint_runs_check_before_uvicorn(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log_file = tmp_path / "calls.log"

    python_bin = bin_dir / "python"
    python_bin.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "printf 'python:%s\\n' \"$*\" >> \"$CALL_LOG\"\n"
        "exit 0\n",
        encoding="utf-8",
    )
    python_bin.chmod(0o755)

    uvicorn_bin = bin_dir / "uvicorn"
    uvicorn_bin.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "printf 'uvicorn:%s\\n' \"$*\" >> \"$CALL_LOG\"\n"
        "exit 0\n",
        encoding="utf-8",
    )
    uvicorn_bin.chmod(0o755)

    env = os.environ.copy()
    env.update(
        {
            "CALL_LOG": str(log_file),
            "PYTHON_BIN": str(python_bin),
            "UVICORN_BIN": str(uvicorn_bin),
            "WORK_ROOT": str(tmp_path / "work"),
            "LOG_DIR": str(tmp_path / "logs"),
        }
    )

    result = subprocess.run(
        ["bash", "scripts/entrypoint.sh"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    calls = log_file.read_text(encoding="utf-8").splitlines()
    assert calls[0] == "python:-u -m document_conversion.interfaces.cli check-system"
    assert calls[1].startswith("uvicorn:document_conversion.interfaces.api.app:app ")


def test_entrypoint_exits_when_check_system_fails(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log_file = tmp_path / "calls.log"

    python_bin = bin_dir / "python"
    python_bin.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "printf 'python:%s\\n' \"$*\" >> \"$CALL_LOG\"\n"
        "exit 1\n",
        encoding="utf-8",
    )
    python_bin.chmod(0o755)

    uvicorn_bin = bin_dir / "uvicorn"
    uvicorn_bin.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "printf 'uvicorn:%s\\n' \"$*\" >> \"$CALL_LOG\"\n"
        "exit 0\n",
        encoding="utf-8",
    )
    uvicorn_bin.chmod(0o755)

    env = os.environ.copy()
    env.update(
        {
            "CALL_LOG": str(log_file),
            "PYTHON_BIN": str(python_bin),
            "UVICORN_BIN": str(uvicorn_bin),
            "WORK_ROOT": str(tmp_path / "work"),
            "LOG_DIR": str(tmp_path / "logs"),
        }
    )

    result = subprocess.run(
        ["bash", "scripts/entrypoint.sh"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    calls = log_file.read_text(encoding="utf-8").splitlines()
    assert calls == ["python:-u -m document_conversion.interfaces.cli check-system"]


def test_dockerfile_contains_build_time_runtime_assertions() -> None:
    dockerfile = Path(__file__).resolve().parents[2] / "Dockerfile"
    content = dockerfile.read_text(encoding="utf-8")

    assert "test -f \"$DOCX2TEX_HOME/xpl/docx2tex.xpl\"" in content
    assert "/opt/venv/bin/python -u -m document_conversion.interfaces.cli check-system" in content
