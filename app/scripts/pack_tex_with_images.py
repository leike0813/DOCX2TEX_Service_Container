import argparse
import re
import shutil
from pathlib import Path

# Match full include, capture optional [options] and {path}
INCLUDE_RE = re.compile(
    r"""(\\includegraphics\*?)          # cmd
         (\s*\[[^\]]*\])?               # [options]
         \s*\{([^\}]+)\}                # {path}
    """,
    re.IGNORECASE | re.VERBOSE,
)


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
    """Resolve referenced path to existing file.
    Search order:
      1) tex_dir / raw_path
      2) <stem>.docx.tmp/**/<basename>
      3) <stem>.debug/**/<basename>
      4) try common ext variants (.pdf .png .jpg .jpeg .eps)
    """
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
        # Try with common extensions
        for ext in common_exts:
            cc = c.with_suffix(ext) if ext else c
            if cc.exists():
                return cc
    return None


def _normalize_width_options(text: str) -> str:
    # Normalize width=1\textwidth or width=1.0\textwidth (and possible doubled backslashes)
    text = re.sub(r"(width\s*=\s*)1(?:\.0+)?\s*\\+textwidth", r"\1\\textwidth", text, flags=re.IGNORECASE)
    # Also normalize common linewidth variant if present
    text = re.sub(r"(width\s*=\s*)1(?:\.0+)?\s*\\+linewidth", r"\1\\linewidth", text, flags=re.IGNORECASE)
    return text


def rewrite_and_collect(tex_path: Path, image_dir: Path) -> tuple[int, int]:
    tex_dir = tex_path.parent
    stem_dir = tex_dir / tex_path.stem
    image_dir.mkdir(parents=True, exist_ok=True)
    content = tex_path.read_text(encoding="utf-8", errors="replace")

    copied: dict[str, str] = {}  # src -> new name
    removed_vsdx = 0

    def repl_func(match: re.Match) -> str:
        nonlocal removed_vsdx
        cmd = match.group(1)
        opt = match.group(2) or ""
        inner = match.group(3)
        raw = inner
        # Drop Visio sources entirely
        if Path(_unescape_tex_path(raw)).suffix.lower() == ".vsdx":
            removed_vsdx += 1
            return ""  # remove the whole includegraphics command
        # Already points to image/ -> leave as-is (will be packaged later)
        if raw.replace("\\", "/").startswith("image/"):
            return match.group(0)
        src = _find_source(tex_dir, stem_dir, raw)
        if not src:
            return match.group(0)  # keep original if not found
        # Skip copying .vsdx defensively (should have been caught above)
        if src.suffix.lower() == ".vsdx":
            removed_vsdx += 1
            return ""
        new_name = _ensure_unique(image_dir, src.name)
        dst = image_dir / new_name
        if str(src) not in copied:
            shutil.copy2(src, dst)
            copied[str(src)] = new_name
        new_ref = f"image/{copied[str(src)]}"
        return f"{cmd}{opt}{{{new_ref}}}"

    new_content = INCLUDE_RE.sub(repl_func, content)
    new_content = _normalize_width_options(new_content)

    if new_content != content:
        bak = tex_path.with_suffix(tex_path.suffix + ".bak2")
        shutil.copyfile(tex_path, bak)
        tex_path.write_text(new_content, encoding="utf-8")

    return len(copied), removed_vsdx


def main():
    ap = argparse.ArgumentParser(
        description=(
            "Collect referenced images to ./image, rewrite TeX include paths, "
            "drop .vsdx includes, and normalize width options"
        )
    )
    ap.add_argument("tex", help="Path to .tex file")
    ap.add_argument("--image-dir", default="image")
    args = ap.parse_args()

    tex = Path(args.tex).resolve()
    if not tex.exists():
        raise SystemExit(f"tex not found: {tex}")
    out_dir = (tex.parent / args.image_dir).resolve()
    n, dropped = rewrite_and_collect(tex, out_dir)
    print(f"[pack] collected_images={n} dropped_vsdx_includes={dropped} image_dir={out_dir}")


if __name__ == "__main__":
    main()
