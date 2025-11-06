import argparse
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


INCLUDE_RE = re.compile(
    r"""\\includegraphics\*?      # \\includegraphics or \\includegraphics*
        \s*(?:\[[^\]]*\])?   # optional [options]
        \s*\{([^}]+)\}        # {path}
    """,
    re.IGNORECASE | re.VERBOSE,
)


def unescape_tex_path(p: str) -> str:
    # Reverse common escapes for filesystem lookup
    return p.replace(r"\%", "%").replace(r"\#", "#")


def escape_tex_path(p: str) -> str:
    # Escape TeX-sensitive characters in paths we emit back
    return p.replace("%", r"\%").replace("#", r"\#")


def find_existing_with_exts(base_no_ext: Path, exts: List[str]) -> Optional[Path]:
    for ext in exts:
        cand = base_no_ext.with_suffix(ext)
        if cand.exists():
            return cand
    return None


def collect_graphics_references(tex_content: str) -> List[str]:
    return [m.group(1) for m in INCLUDE_RE.finditer(tex_content)]


def resolve_reference(tex_dir: Path, ref: str, search_exts: List[str]) -> Tuple[Optional[Path], Optional[str]]:
    """Return (existing_path, explicit_ext_or_none)
    explicit_ext_or_none is the extension present in TeX (including the dot), or None if omitted.
    """
    unescaped = unescape_tex_path(ref)
    p = Path(unescaped)
    explicit_ext = p.suffix if p.suffix else None
    if not p.is_absolute():
        p = (tex_dir / p)
    # If TeX had extension, trust it
    if explicit_ext:
        if p.exists():
            return (p.resolve(), explicit_ext)
        return (None, explicit_ext)
    # No extension → probe common ones
    found = find_existing_with_exts(p, search_exts)
    return (found.resolve() if found else None, None)


def unique_dest_name(dest_dir: Path, base_name: str, used: Set[str]) -> str:
    name = base_name
    stem = Path(base_name).stem
    suffix = Path(base_name).suffix
    i = 1
    while name in used or (dest_dir / name).exists():
        name = f"{stem}-{i}{suffix}"
        i += 1
    used.add(name)
    return name


def pack(tex_path: Path, image_dir_name: str = "image") -> None:
    tex_path = tex_path.resolve()
    tex_dir = tex_path.parent
    content = tex_path.read_text(encoding="utf-8", errors="replace")

    # Collect references from TeX
    refs = collect_graphics_references(content)
    if not refs:
        # Nothing to do, but ensure empty image dir not created
        return

    # Target directory
    out_dir = tex_dir / image_dir_name
    out_dir.mkdir(parents=True, exist_ok=True)

    # Map raw TeX ref → new TeX ref (rewritten to image/<file>)
    replacements: Dict[str, str] = {}
    # Avoid filename collisions
    used_names: Set[str] = set()

    # Search order for implicit extensions
    search_exts = [
        ".pdf",
        ".png",
        ".jpg",
        ".jpeg",
        ".eps",
        ".svg",
        ".bmp",
        ".wmf",
        ".emf",
    ]

    for raw in refs:
        src_path, explicit_ext = resolve_reference(tex_dir, raw, search_exts)
        if not src_path or not src_path.exists():
            # Leave as-is if unresolved
            continue

        # Destination file name: keep basename; deduplicate
        dest_name = unique_dest_name(out_dir, src_path.name, used_names)
        dest_path = out_dir / dest_name
        if src_path.resolve() != dest_path.resolve():
            shutil.copy2(src_path, dest_path)

        # Build new TeX ref pointing to image/<dest_name>
        new_ref = f"{image_dir_name}/{dest_name}"

        # Preserve TeX omission of extension: if original had no extension, strip it from new ref
        if explicit_ext is None:
            new_ref = str(Path(new_ref).with_suffix(""))

        replacements[raw] = escape_tex_path(new_ref)

    if not replacements:
        return

    # Write backup
    bak = tex_path.with_suffix(tex_path.suffix + ".bak")
    shutil.copyfile(tex_path, bak)

    # Apply replacements only inside \includegraphics{...}
    def repl_func(m: re.Match) -> str:
        inner = m.group(1)
        new_inner = replacements.get(inner, inner)
        return m.group(0).replace(inner, new_inner, 1)

    new_content = INCLUDE_RE.sub(repl_func, content)
    tex_path.write_text(new_content, encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="Pack TeX with referenced images into ./image and rewrite \includegraphics paths.")
    ap.add_argument("tex", help="Path to .tex file")
    ap.add_argument("--image-dir", default="image", help="Target image directory name (default: image)")
    args = ap.parse_args()

    tex_path = Path(args.tex)
    if not tex_path.exists():
        raise SystemExit(f"TeX not found: {tex_path}")
    pack(tex_path, args.image_dir)


if __name__ == "__main__":
    main()

