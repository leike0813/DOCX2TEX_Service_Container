from __future__ import annotations

from pathlib import Path
import tempfile

from app.core.postprocess import (
    release_collect_images_and_normalize,
    debug_comment_vsdx_and_normalize,
)


def _write(p: Path, s: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")


def test_release_collect_images_rewrites_and_drops_vsdx():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        tex = td / "doc.tex"
        imgdir = td / "assets"
        imgdir.mkdir(parents=True, exist_ok=True)
        # prepare a real png file (empty but exists)
        png = imgdir / "a.png"
        png.write_bytes(b"\x89PNG\r\n\x1a\n")
        content = (
            r"\includegraphics[width=1\textwidth]{assets/a.png}\n"
            + r"\includegraphics{diagram.vsdx}\n"
        )
        _write(tex, content)

        ncol, ndrop = release_collect_images_and_normalize(tex, tex.parent / "image")
        assert ncol >= 1 and ndrop >= 1
        new_text = tex.read_text(encoding="utf-8")
        # width normalized (1\textwidth -> \textwidth)
        assert "width=\\textwidth" in new_text
        # vsdx include removed entirely
        assert "diagram.vsdx" not in new_text
        # png path rewritten into image/
        assert "image/" in new_text
        # image copied
        assert any(p.suffix.lower() == ".png" for p in (tex.parent / "image").iterdir())


def test_debug_comment_vsdx_and_normalize_width():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        tex = td / "doc.tex"
        content = (
            r"\includegraphics[width=1.0\textwidth]{foo.png}\n"
            + r"\includegraphics{shape.VSDX}\n"
        )
        _write(tex, content)
        commented, _ = debug_comment_vsdx_and_normalize(tex)
        assert commented >= 1
        new_text = tex.read_text(encoding="utf-8")
        # width normalized
        assert "width=\\textwidth" in new_text
        # vsdx line is commented out
        assert "% \\includegraphics" in new_text or "shape.VSDX" in new_text and "%" in new_text.split("shape.VSDX")[0]

