import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

INCLUDE_RE = re.compile(
    r"""\\includegraphics\*?   # \includegraphics or \includegraphics*
        \s*(?:\[[^\]]*\])?    # optional [options]
        \s*\{([^\}]+)\}       # {path}
    """,
    re.IGNORECASE | re.VERBOSE,
)

def detect_inkscape_cmd(inkscape_hint: str | None) -> list[str]:
    cmd = [inkscape_hint] if inkscape_hint else ["inkscape"]
    try:
        out = subprocess.run(cmd + ["--version"], capture_output=True, text=True, check=True)
        ver = out.stdout.strip()
        # Parse first number token, default to 1.x behavior
        m = re.search(r"(\d+)\.(\d+)", ver)
        major = int(m.group(1)) if m else 1
        if major >= 1:
            return cmd + ["--batch-process"]
        else:
            return cmd  # legacy syntax
    except Exception as e:
        print(f"[WARN] Could not detect Inkscape version ({e}). Assuming >=1.0 CLI.", file=sys.stderr)
        return cmd + ["--batch-process"]

def convert_with_inkscape(inkscape_base: list[str], src: Path, dst: Path) -> bool:
    dst.parent.mkdir(parents=True, exist_ok=True)
    # Choose CLI based on version probe
    try:
        if "--batch-process" in inkscape_base:
            # Inkscape >= 1.0
            cmd = inkscape_base[:-1] + [  # remove --batch-process from base to avoid duplication
                str(src),
                "--export-type=pdf",
                f"--export-filename={str(dst)}",
            ]
        else:
            # Inkscape 0.9x
            cmd = inkscape_base + ["-z", "-f", str(src), "-A", str(dst)]
        print(f"[INFO] Converting: {src} -> {dst}")
        cp = subprocess.run(cmd, capture_output=True, text=True)
        if cp.returncode != 0:
            print(f"[ERROR] Inkscape failed for {src}:\n{cp.stdout}\n{cp.stderr}", file=sys.stderr)
            return False
        return True
    except FileNotFoundError:
        print("[ERROR] Inkscape not found. Add to PATH or pass --inkscape path.", file=sys.stderr)
        return False

def unescape_tex_path(p: str) -> str:
    # docx2tex会把 % 和 # 转义为 \% \#；用于文件系统匹配时需要还原
    return p.replace(r"\%", "%").replace(r"\#", "#")

def replace_ext_keep_escapes(original: str, new_ext: str) -> str:
    # 只替换末尾扩展名（不动前面的转义）
    return re.sub(r"\.(emf|wmf)$", f".{new_ext}", original, flags=re.IGNORECASE)

def find_existing_with_exts(base_no_ext: Path, exts: list[str]) -> Path | None:
    for ext in exts:
        cand = base_no_ext.with_suffix(ext)
        if cand.exists():
            return cand
    return None

def process_tex(tex_path: Path, inkscape_hint: str | None) -> None:
    tex_path = tex_path.resolve()
    tex_dir = tex_path.parent
    content = tex_path.read_text(encoding="utf-8", errors="replace")

    inkscape_cmd_base = detect_inkscape_cmd(inkscape_hint)

    replacements: dict[str, str] = {}
    converted: set[Path] = set()
    errors: list[str] = []

    for m in INCLUDE_RE.finditer(content):
        raw_include = m.group(1)  # 原始大括号内文本（可能含 \% \#）
        unescaped = unescape_tex_path(raw_include)

        # 解析绝对/相对路径
        ref_path = Path(unescaped)
        if not ref_path.is_absolute():
            ref_path = (tex_dir / ref_path).resolve()

        # 情况1：显式 .emf/.wmf/.svg
        if ref_path.suffix.lower() in {".emf", ".wmf", ".svg"}:
            src = ref_path
            dst = ref_path.with_suffix(".pdf")
            if src.exists():
                ok = convert_with_inkscape(inkscape_cmd_base, src, dst)
                if ok:
                    converted.add(dst)
                    new_tex_ref = replace_ext_keep_escapes(raw_include, "pdf")
                    replacements[raw_include] = new_tex_ref
                else:
                    errors.append(str(src))
            else:
                errors.append(f"missing:{src}")
            continue

        # 情况2：无扩展或非目标扩展，但磁盘上存在同名 .emf/.wmf
        if ref_path.suffix == "":
            found = find_existing_with_exts(ref_path, [".emf", ".wmf", ".svg"])
            if found:
                dst = found.with_suffix(".pdf")
                ok = convert_with_inkscape(inkscape_cmd_base, found, dst)
                if ok:
                    converted.add(dst)
                    # 在 TeX 中显式加上 .pdf 扩展
                    new_tex_ref = raw_include + ".pdf"
                    replacements[raw_include] = new_tex_ref
                else:
                    errors.append(str(found))

    if not replacements:
        print("[INFO] No .emf/.wmf references found in TeX.")
        return

    # 备份
    bak = tex_path.with_suffix(tex_path.suffix + ".bak")
    shutil.copyfile(tex_path, bak)
    print(f"[INFO] Backup written: {bak}")

    # 应用替换（避免重复替换冲突，按长到短排序）
    def repl_func(match: re.Match) -> str:
        inner = match.group(1)
        new_inner = replacements.get(inner, inner)
        return match.group(0).replace(inner, new_inner, 1)

    new_content = INCLUDE_RE.sub(repl_func, content)
    tex_path.write_text(new_content, encoding="utf-8")
    print(f"[INFO] Updated TeX written: {tex_path}")

    if converted:
        print("[INFO] Converted files:")
        for p in sorted(converted):
            print("  -", p)
    if errors:
        print("[WARN] Some conversions failed or files missing:")
        for e in errors:
            print("  -", e)

def main():
    ap = argparse.ArgumentParser(description="Convert EMF/WMF in TeX to PDF via Inkscape and fix \\includegraphics refs.")
    ap.add_argument("tex", help="Path to .tex file")
    ap.add_argument("--inkscape", help="Path to inkscape executable (optional)")
    args = ap.parse_args()

    tex_path = Path(args.tex)
    if not tex_path.exists():
        print(f"[ERROR] TeX file not found: {tex_path}", file=sys.stderr)
        sys.exit(1)
    process_tex(tex_path, args.inkscape)

if __name__ == "__main__":
    main()
