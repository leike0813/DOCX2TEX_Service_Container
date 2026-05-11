from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path
from zipfile import ZipFile

from document_conversion.infrastructure.process import run_subprocess
from document_conversion.infrastructure.state import JobState
from engines.docx2tex_engine.assets import resolve_conf_assets_root
from engines.docx2tex_engine.packaging import ArtifactPackager
from engines.docx2tex_engine.postprocess import (
    debug_comment_vsdx_and_normalize,
    release_collect_images_and_normalize,
)
from engines.docx2tex_engine.stylemap import prepare_effective_xsls


def test_run_subprocess_python_ok():
    rc, out, _ = run_subprocess([sys.executable, "-c", "print('OK')"], timeout=10)
    assert rc == 0
    assert "OK" in out


def test_postprocess_release_and_debug_modes():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        tex = root / "doc.tex"
        assets = root / "assets"
        assets.mkdir(parents=True, exist_ok=True)
        (assets / "a.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        (assets / "oleObject6.bin").write_bytes(b"OLE")
        tex.write_text(
            "\\includegraphics[width=1\\textwidth]{assets/a.png}\n"
            "\\includegraphics{assets/oleObject6.bin}\n"
            "\\includegraphics{diagram.vsdx}\n",
            encoding="utf-8",
        )
        release_summary = release_collect_images_and_normalize(tex, root / "image")
        assert release_summary.copied_images >= 1
        assert release_summary.dropped_vsdx >= 1
        assert release_summary.commented_ole_binary_refs == 1
        assert release_summary.skipped_ole_binary_assets == 1
        release_text = tex.read_text(encoding="utf-8")
        assert "image/" in release_text
        assert "omitted uncompilable OLE object reference" in release_text
        assert "% \\includegraphics{assets/oleObject6.bin}" in release_text

        tex.write_text(
            "\\includegraphics[width=1.0\\textwidth]{foo.png}\n"
            "\\includegraphics{oleObject7.bin}\n"
            "\\includegraphics{shape.VSDX}\n",
            encoding="utf-8",
        )
        debug_summary = debug_comment_vsdx_and_normalize(tex)
        assert debug_summary.commented_vsdx >= 1
        assert debug_summary.commented_ole_binary_refs == 1
        debug_text = tex.read_text(encoding="utf-8")
        assert "width=\\textwidth" in debug_text
        assert "omitted uncompilable OLE object reference" in debug_text


def test_packager_manifest_excludes_ole_binary_assets_from_release_bundle():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        public_root = root / "public"
        work_dir = root / "task"
        image_dir = work_dir / "assets"
        image_dir.mkdir(parents=True, exist_ok=True)
        (image_dir / "image11.pdf").write_bytes(b"%PDF-1.4")
        (image_dir / "oleObject6.bin").write_bytes(b"OLE")

        out_tex = work_dir / "sample.tex"
        out_tex.write_text(
            "\\includegraphics[width=\\textwidth]{assets/image11.pdf}\n"
            "\\includegraphics[width=\\textwidth]{assets/oleObject6.bin}\n",
            encoding="utf-8",
        )
        out_xml = work_dir / "sample.xml"
        out_xml.write_text("<hub/>", encoding="utf-8")
        log_path = root / "logs" / "task.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("ok\n", encoding="utf-8")

        result_zip = ArtifactPackager(public_root).package(
            task_id="task-1",
            job_state=JobState(
                task_id="task-1",
                state="packaging",
                start_time=time.time(),
                work_dir=str(work_dir),
            ),
            basename="sample",
            work_dir=work_dir,
            out_tex=out_tex,
            out_xml=out_xml,
            debug=False,
            img_post_proc=True,
            image_dir="image",
            log_path=log_path,
            mtef_source="ole+wmf",
            table_model="tabularx",
            fontmaps_dir=None,
        )

        with ZipFile(result_zip, "r") as archive:
            names = set(archive.namelist())
            manifest = archive.read("manifest.json").decode("utf-8")
            tex_text = archive.read("sample.tex").decode("utf-8")

        assert "sample.tex" in names
        assert "image/image11.pdf" in names
        assert "image/oleObject6.bin" not in names
        assert '"ole_binary_refs_commented": 1' in manifest
        assert '"ole_binary_assets_skipped": 1' in manifest
        assert "omitted uncompilable OLE object reference" in tex_text


def test_builtin_docx2tex_confs_suppress_ole_binary_placeholders():
    conf_root = resolve_conf_assets_root()
    for name in [
        "conf-book-en.xml",
        "conf-ctexart-zh.xml",
        "conf-ctexbook-zh.xml",
        "conf-elsarticle-en.xml",
    ]:
        text = (conf_root / name).read_text(encoding="utf-8")
        assert "OLEObject" in text
        assert "\\\\.bin$" in text


def test_prepare_effective_xsls():
    with tempfile.TemporaryDirectory() as td:
        work_dir = Path(td)
        conf = resolve_conf_assets_root() / "conf-ctexbook-zh.xml"
        effective, style_map, role_cmds = prepare_effective_xsls(
            '{"Title":"Main Title","Heading1":"Level 1 Heading"}',
            [conf],
            user_custom_evolve=None,
            work_dir=work_dir,
        )
        assert effective is not None and effective.exists()
        assert "Title" in style_map
        assert role_cmds
