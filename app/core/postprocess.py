from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Tuple, Optional


INCLUDE_RE = re.compile(
    r"""(\\includegraphics\*?)          # cmd
         (\s*\[[^\]]*\])?               # [options]
         \s*\{([^\}]+)\}                # {path}
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _normalize_width_options(text: str) -> str:
    text = re.sub(r"(width\s*=\s*)1(?:\.0+)?\s*\\+textwidth", r"\1\\textwidth", text, flags=re.IGNORECASE)
    text = re.sub(r"(width\s*=\s*)1(?:\.0+)?\s*\\+linewidth", r"\1\\linewidth", text, flags=re.IGNORECASE)
    return text


def _unescape_tex_path(p: str) -> str:
    return p.replace(r"\%", "%").replace(r"\#", "#")


def _ensure_unique(dst_dir: Path, filename: str) -> str:
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    candidate = filename
    i = 1
    while (dst_dir / candidate).exists():
        candidate = f"{stem}_{i}{suffix}"
        i += 1
    return candidate


def _find_source(tex_dir: Path, stem_dir: Path, raw_path: str) -> Path | None:
    p = Path(_unescape_tex_path(raw_path))
    candidates: list[Path] = []
    if not p.is_absolute():
        candidates.append((tex_dir / p).resolve())
    else:
        candidates.append(p)

    basename = p.name
    docx_tmp = stem_dir.with_suffix(".docx.tmp")
    debug_dir = stem_dir.with_suffix(".debug")
    if docx_tmp.exists():
        for sub in docx_tmp.rglob(basename):
            candidates.append(sub)
    if debug_dir.exists():
        for sub in debug_dir.rglob(basename):
            candidates.append(sub)

    common_exts = ["", ".pdf", ".png", ".jpg", ".jpeg", ".eps"]
    for c in candidates:
        if c.exists():
            return c
        for ext in common_exts:
            cc = c.with_suffix(ext) if ext else c
            if cc.exists():
                return cc
    return None


def release_collect_images_and_normalize(
    tex_path: Path, image_dir: Path, image_alias: Optional[str] = None
) -> Tuple[int, int]:
    """Non-debug: collect referenced images to image_dir, rewrite include paths,
    drop .vsdx includes, and normalize width options.

    Returns (collected_images, dropped_vsdx_includes).
    """
    tex_dir = tex_path.parent
    stem_dir = tex_dir / tex_path.stem
    image_dir.mkdir(parents=True, exist_ok=True)
    content = tex_path.read_text(encoding="utf-8", errors="replace")

    prefix = (image_alias or image_dir.name).strip("/\\")
    if not prefix:
        prefix = "image"
    copied: dict[str, str] = {}
    removed_vsdx = 0

    def repl_func(match: re.Match) -> str:
        nonlocal removed_vsdx
        cmd = match.group(1)
        opt = match.group(2) or ""
        inner = match.group(3)
        raw = inner
        if Path(_unescape_tex_path(raw)).suffix.lower() == ".vsdx":
            removed_vsdx += 1
            return ""  # remove the whole includegraphics command
        if raw.replace("\\", "/").startswith(f"{prefix}/"):
            return match.group(0)
        src = _find_source(tex_dir, stem_dir, raw)
        if not src:
            return match.group(0)
        if src.suffix.lower() == ".vsdx":
            removed_vsdx += 1
            return ""
        new_name = _ensure_unique(image_dir, src.name)
        dst = image_dir / new_name
        if str(src) not in copied:
            shutil.copy2(src, dst)
            copied[str(src)] = new_name
        new_ref = f"{prefix}/{copied[str(src)]}"
        return f"{cmd}{opt}{{{new_ref}}}"

    new_content = INCLUDE_RE.sub(repl_func, content)
    new_content = _normalize_width_options(new_content)
    if new_content != content:
        tex_path.write_text(new_content, encoding="utf-8")
    return len(copied), removed_vsdx


def debug_comment_vsdx_and_normalize(tex_path: Path) -> Tuple[int, int]:
    """Debug: comment out .vsdx includes and normalize width options.
    Returns (commented_vsdx, 0).
    """
    content = tex_path.read_text(encoding="utf-8", errors="replace")
    commented = 0

    def _comment(s: str) -> str:
        s = s.strip()
        return "\n% " + s + "\n"

    def repl(m: re.Match) -> str:
        nonlocal commented
        whole = m.group(0)
        inner = m.group(3)
        if inner.lower().endswith('.vsdx'):
            commented += 1
            return _comment(whole)
        return whole

    new_content = INCLUDE_RE.sub(repl, content)
    new_content = _normalize_width_options(new_content)
    if new_content != content:
        tex_path.write_text(new_content, encoding="utf-8")
    return commented, 0


# --- Vector reference conversion (EMF/WMF/SVG -> PDF) ---

def _detect_inkscape_cmd(inkscape_hint: Optional[str]) -> list[str]:
    import subprocess, sys
    cmd = [inkscape_hint] if inkscape_hint else ["inkscape"]
    try:
        out = subprocess.run(cmd + ["--version"], capture_output=True, text=True, check=True)
        ver = out.stdout.strip()
        m = re.search(r"(\d+)\.(\d+)", ver)
        major = int(m.group(1)) if m else 1
        if major >= 1:
            return cmd + ["--batch-process"]
        else:
            return cmd
    except Exception:
        return cmd + ["--batch-process"]


def _convert_with_inkscape(inkscape_base: list[str], src: Path, dst: Path) -> bool:
    import subprocess
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        if "--batch-process" in inkscape_base:
            cmd = inkscape_base[:-1] + [
                str(src),
                "--export-type=pdf",
                f"--export-filename={str(dst)}",
            ]
        else:
            cmd = inkscape_base + ["-z", "-f", str(src), "-A", str(dst)]
        cp = subprocess.run(cmd, capture_output=True, text=True)
        return cp.returncode == 0
    except FileNotFoundError:
        return False


def convert_vector_references(tex_path: Path, inkscape_hint: Optional[str] = None) -> Tuple[int, int, int]:
    """Convert emf/wmf/svg references in TeX to PDF using Inkscape and update paths.
    Returns (converted_count, missing_count, failed_count).
    """
    tex_path = tex_path.resolve()
    tex_dir = tex_path.parent
    content = tex_path.read_text(encoding="utf-8", errors="replace")
    inkscape_cmd_base = _detect_inkscape_cmd(inkscape_hint)
    replacements: dict[str, str] = {}
    converted: int = 0
    missing: int = 0
    failed: int = 0

    for m in INCLUDE_RE.finditer(content):
        raw_include = m.group(3)
        unescaped = _unescape_tex_path(raw_include)
        ref_path = Path(unescaped)
        if not ref_path.is_absolute():
            ref_path = (tex_dir / ref_path).resolve()
        ext = ref_path.suffix.lower()
        if ext in {".emf", ".wmf", ".svg"} or ext == "":
            src = ref_path
            if ext == "":
                # try probe
                for e in (".emf", ".wmf", ".svg"):
                    cand = ref_path.with_suffix(e)
                    if cand.exists():
                        src = cand
                        ext = e
                        break
            if not src.exists():
                missing += 1
                continue
            dst = src.with_suffix(".pdf")
            ok = _convert_with_inkscape(inkscape_cmd_base, src, dst)
            if ok:
                converted += 1
                # Update reference to .pdf
                if raw_include.endswith(tuple([".emf", ".wmf", ".svg"])):
                    replacements[raw_include] = raw_include[:-4] + ".pdf"
                else:
                    replacements[raw_include] = raw_include + ".pdf"
            else:
                failed += 1

    if replacements:
        def repl_func(match: re.Match) -> str:
            inner = match.group(3)
            new_inner = replacements.get(inner, inner)
            return match.group(0).replace(inner, new_inner, 1)

        new_content = INCLUDE_RE.sub(repl_func, content)
        tex_path.write_text(new_content, encoding="utf-8")
    return converted, missing, failed
