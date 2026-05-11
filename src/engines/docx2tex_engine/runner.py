from __future__ import annotations

import os
import shlex
from dataclasses import dataclass
from pathlib import Path

from document_conversion.infrastructure.config import Config
from document_conversion.infrastructure.logging import log_line
from document_conversion.infrastructure.process import run_subprocess


@dataclass(frozen=True)
class RunnerRequest:
    work_dir: Path
    orig_name: str
    debug: bool
    conf_file: Path | None
    custom_xsl: Path | None
    custom_evolve: Path | None
    mtef_source: str | None
    table_model: str | None
    fontmaps_dir: Path | None


@dataclass(frozen=True)
class RunnerOutput:
    basename: str
    out_tex: Path
    out_xml: Path
    debug_dir: Path
    csv_path: Path


class Docx2TexRunner:
    def __init__(self, cfg: Config):
        self.cfg = cfg

    def run(self, request: RunnerRequest, log_path: Path) -> RunnerOutput:
        basename = Path(request.orig_name or "document.docx").stem
        out_tex = request.work_dir / f"{basename}.tex"
        out_xml = request.work_dir / f"{basename}.xml"
        debug_dir = request.work_dir / f"{basename}.debug"
        chosen_conf = request.conf_file or (self.cfg.docx2tex_home / "conf" / "conf.xml")

        env = {
            "XML_CATALOG_FILES": str(self.cfg.catalog_file),
            "PATH": os.environ.get("PATH", ""),
            "JAVA_TOOL_OPTIONS": os.environ.get("JAVA_TOOL_OPTIONS", ""),
        }
        cmd = [str(self.cfg.docx2tex_home / "calabash" / "calabash.sh")]
        option_args = [
            f"docx={(request.work_dir / request.orig_name).resolve().as_uri()}",
            f"conf={chosen_conf.as_uri()}",
            f"debug={'yes' if request.debug else 'no'}",
            f"debug-dir-uri={debug_dir.resolve().as_uri()}",
        ]
        if request.custom_evolve and request.custom_evolve.exists():
            cmd.extend(
                [
                    "-i",
                    f"custom-evolve-hub-driver={request.custom_evolve.resolve().as_uri()}",
                ]
            )
        if request.custom_xsl and request.custom_xsl.exists():
            option_args.append(f"custom-xsl={request.custom_xsl.resolve().as_uri()}")
        if request.mtef_source:
            option_args.append(f"mtef-source={request.mtef_source}")
        if request.table_model:
            option_args.append(f"table-model={request.table_model}")
        if request.fontmaps_dir and request.fontmaps_dir.exists():
            option_args.append(f"custom-font-maps-dir={request.fontmaps_dir.resolve().as_uri()}")
        cmd.extend(["-o", f"result={out_tex.resolve().as_uri()}"])
        cmd.extend(["-o", f"hub={out_xml.resolve().as_uri()}"])
        cmd.append(str(self.cfg.docx2tex_home / "xpl" / "docx2tex.xpl"))
        cmd.extend(option_args)
        with open(log_path, "ab") as handle:
            handle.write(b"\n--- calabash_cmd ---\n")
            handle.write((" ".join(shlex.quote(item) for item in cmd) + "\n").encode("utf-8"))
        return_code, stdout, stderr = run_subprocess(
            cmd,
            cwd=self.cfg.docx2tex_home,
            env=env,
            timeout=1200,
        )
        with open(log_path, "ab") as handle:
            handle.write(b"\n--- calabash ---\n")
            handle.write((stdout or "").encode("utf-8"))
            handle.write(b"\n")
            handle.write((stderr or "").encode("utf-8"))
        if return_code != 0 or not out_tex.exists():
            raise RuntimeError(stderr or "docx2tex failed")
        log_line(log_path, "docx2tex completed")
        return RunnerOutput(
            basename=basename,
            out_tex=out_tex,
            out_xml=out_xml,
            debug_dir=debug_dir,
            csv_path=request.work_dir / f"{basename}.csv",
        )
