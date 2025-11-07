import argparse
import re
import shutil
from pathlib import Path

INCLUDE_RE = re.compile(
    r"""(\\includegraphics\*?)          # cmd
         (\s*\[[^\]]*\])?               # [options]
         \s*\{([^\}]+)\}                # {path}
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _normalize_width_options(text: str) -> str:
    # Normalize width=1\textwidth or width=1.0\textwidth (and possible doubled backslashes)
    text = re.sub(r"(width\s*=\s*)1(?:\.0+)?\s*\\+textwidth", r"\1\\textwidth", text, flags=re.IGNORECASE)
    # Also handle linewidth variant if present
    text = re.sub(r"(width\s*=\s*)1(?:\.0+)?\s*\\+linewidth", r"\1\\linewidth", text, flags=re.IGNORECASE)
    return text


def _comment(s: str) -> str:
    # Produce a TeX comment line for the given snippet
    # Ensure it starts on a new line for readability
    s = s.strip()
    return "\n% " + s + "\n"


def process(tex_path: Path) -> tuple[int, int]:
    content = tex_path.read_text(encoding="utf-8", errors="replace")
    removed_vsdx = 0

    def repl_func(m: re.Match) -> str:
        nonlocal removed_vsdx
        whole = m.group(0)
        cmd = m.group(1)
        opt = m.group(2) or ""
        inner = m.group(3)
        # If it's a Visio .vsdx include: comment out original, no replacement
        if inner.lower().endswith('.vsdx'):
            removed_vsdx += 1
            return _comment(whole)
        # For other includes: leave as-is; width normalization runs after regex substitution
        return whole

    new_content = INCLUDE_RE.sub(repl_func, content)
    new_content = _normalize_width_options(new_content)

    if new_content != content:
        bak = tex_path.with_suffix(tex_path.suffix + ".bak_debug")
        shutil.copyfile(tex_path, bak)
        tex_path.write_text(new_content, encoding="utf-8")

    return removed_vsdx, 0


def main():
    ap = argparse.ArgumentParser(description="Debug rewrite: comment out .vsdx includes and normalize width options in TeX")
    ap.add_argument("tex", help="Path to .tex file")
    args = ap.parse_args()

    tex = Path(args.tex).resolve()
    if not tex.exists():
        raise SystemExit(f"tex not found: {tex}")
    dropped, _ = process(tex)
    print(f"[rewrite-debug] dropped_vsdx_includes={dropped} tex={tex}")


if __name__ == "__main__":
    main()
