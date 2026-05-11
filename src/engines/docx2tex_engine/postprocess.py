from __future__ import annotations

import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path


INCLUDE_RE = re.compile(
    r"""(\\includegraphics\*?)
         (\s*\[[^\]]*\])?
         \s*\{([^\}]+)\}
    """,
    re.IGNORECASE | re.VERBOSE,
)
UNCOMPILABLE_OLE_NOTE = "omitted uncompilable OLE object reference"


@dataclass
class PostprocessSummary:
    copied_images: int = 0
    dropped_vsdx: int = 0
    commented_vsdx: int = 0
    commented_ole_binary_refs: int = 0
    ole_binary_ref_paths: list[str] = field(default_factory=list)
    skipped_ole_binary_assets: int = 0
    ole_binary_asset_paths: list[str] = field(default_factory=list)


def _normalize_width_options(text: str) -> str:
    text = re.sub(
        r"(width\s*=\s*)1(?:\.0+)?\s*\\+textwidth",
        r"\1\\textwidth",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"(width\s*=\s*)1(?:\.0+)?\s*\\+linewidth",
        r"\1\\linewidth",
        text,
        flags=re.IGNORECASE,
    )
    return text


def _unescape_tex_path(path: str) -> str:
    return path.replace(r"\%", "%").replace(r"\#", "#")


def _is_ole_binary_ref(path: str) -> bool:
    return Path(_unescape_tex_path(path)).suffix.lower() == ".bin"


def _comment_out_includegraphics(match: re.Match, note: str) -> str:
    return f"\n% {note}\n% {match.group(0).strip()}\n"


def _ensure_unique(dst_dir: Path, filename: str) -> str:
    stem = Path(filename).stem
    suffix = Path(filename).suffix
    candidate = filename
    index = 1
    while (dst_dir / candidate).exists():
        candidate = f"{stem}_{index}{suffix}"
        index += 1
    return candidate


def _find_source(tex_dir: Path, stem_dir: Path, raw_path: str) -> Path | None:
    path = Path(_unescape_tex_path(raw_path))
    candidates: list[Path] = [(tex_dir / path).resolve()] if not path.is_absolute() else [path]
    basename = path.name
    for extra_dir in (stem_dir.with_suffix(".docx.tmp"), stem_dir.with_suffix(".debug")):
        if extra_dir.exists():
            candidates.extend(extra_dir.rglob(basename))
    for candidate in candidates:
        if candidate.exists():
            return candidate
        for extension in ("", ".pdf", ".png", ".jpg", ".jpeg", ".eps"):
            probe = candidate.with_suffix(extension) if extension else candidate
            if probe.exists():
                return probe
    return None


def release_collect_images_and_normalize(
    tex_path: Path,
    image_dir: Path,
    image_alias: str | None = None,
) -> PostprocessSummary:
    tex_dir = tex_path.parent
    stem_dir = tex_dir / tex_path.stem
    image_dir.mkdir(parents=True, exist_ok=True)
    content = tex_path.read_text(encoding="utf-8", errors="replace")
    prefix = (image_alias or image_dir.name).strip("/\\") or "image"
    copied: dict[str, str] = {}
    summary = PostprocessSummary()

    def repl(match: re.Match) -> str:
        command, options, inner = match.group(1), match.group(2) or "", match.group(3)
        if _is_ole_binary_ref(inner):
            source = _find_source(tex_dir, stem_dir, inner)
            summary.commented_ole_binary_refs += 1
            summary.ole_binary_ref_paths.append(inner)
            if source is not None:
                summary.skipped_ole_binary_assets += 1
                summary.ole_binary_asset_paths.append(str(source))
            return _comment_out_includegraphics(match, UNCOMPILABLE_OLE_NOTE)
        if Path(_unescape_tex_path(inner)).suffix.lower() == ".vsdx":
            summary.dropped_vsdx += 1
            return ""
        if inner.replace("\\", "/").startswith(f"{prefix}/"):
            return match.group(0)
        source = _find_source(tex_dir, stem_dir, inner)
        if not source:
            return match.group(0)
        if source.suffix.lower() == ".vsdx":
            summary.dropped_vsdx += 1
            return ""
        if source.suffix.lower() == ".bin":
            summary.commented_ole_binary_refs += 1
            summary.ole_binary_ref_paths.append(inner)
            summary.skipped_ole_binary_assets += 1
            summary.ole_binary_asset_paths.append(str(source))
            return _comment_out_includegraphics(match, UNCOMPILABLE_OLE_NOTE)
        if str(source) not in copied:
            target_name = _ensure_unique(image_dir, source.name)
            shutil.copy2(source, image_dir / target_name)
            copied[str(source)] = target_name
        return f"{command}{options}{{{prefix}/{copied[str(source)]}}}"

    new_content = _normalize_width_options(INCLUDE_RE.sub(repl, content))
    if new_content != content:
        tex_path.write_text(new_content, encoding="utf-8")
    summary.copied_images = len(copied)
    return summary


def debug_comment_vsdx_and_normalize(tex_path: Path) -> PostprocessSummary:
    content = tex_path.read_text(encoding="utf-8", errors="replace")
    summary = PostprocessSummary()

    def repl(match: re.Match) -> str:
        inner = match.group(3)
        if inner.lower().endswith(".vsdx"):
            summary.commented_vsdx += 1
            return "\n% " + match.group(0).strip() + "\n"
        if _is_ole_binary_ref(inner):
            summary.commented_ole_binary_refs += 1
            summary.ole_binary_ref_paths.append(inner)
            return _comment_out_includegraphics(match, UNCOMPILABLE_OLE_NOTE)
        return match.group(0)

    new_content = _normalize_width_options(INCLUDE_RE.sub(repl, content))
    if new_content != content:
        tex_path.write_text(new_content, encoding="utf-8")
    return summary


def _detect_inkscape_cmd(inkscape_hint: str | None) -> list[str]:
    import subprocess

    command = [inkscape_hint] if inkscape_hint else ["inkscape"]
    try:
        result = subprocess.run(command + ["--version"], capture_output=True, text=True, check=True)
        match = re.search(r"(\d+)\.(\d+)", result.stdout.strip())
        major = int(match.group(1)) if match else 1
        return command + ["--batch-process"] if major >= 1 else command
    except Exception:
        return command + ["--batch-process"]


def _convert_with_inkscape(command: list[str], source: Path, target: Path) -> bool:
    import subprocess

    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        if "--batch-process" in command:
            final_cmd = command[:-1] + [
                str(source),
                "--export-type=pdf",
                f"--export-filename={target}",
            ]
        else:
            final_cmd = command + ["-z", "-f", str(source), "-A", str(target)]
        return subprocess.run(final_cmd, capture_output=True, text=True).returncode == 0
    except FileNotFoundError:
        return False


def convert_vector_references(
    tex_path: Path,
    inkscape_hint: str | None = None,
) -> tuple[int, int, int]:
    tex_path = tex_path.resolve()
    content = tex_path.read_text(encoding="utf-8", errors="replace")
    tex_dir = tex_path.parent
    replacements: dict[str, str] = {}
    converted = 0
    missing = 0
    failed = 0
    inkscape_cmd = _detect_inkscape_cmd(inkscape_hint)
    for match in INCLUDE_RE.finditer(content):
        raw_include = match.group(3)
        ref_path = Path(_unescape_tex_path(raw_include))
        if not ref_path.is_absolute():
            ref_path = (tex_dir / ref_path).resolve()
        extension = ref_path.suffix.lower()
        if extension not in {".emf", ".wmf", ".svg", ""}:
            continue
        source = ref_path
        if extension == "":
            for probe_ext in (".emf", ".wmf", ".svg"):
                probe = ref_path.with_suffix(probe_ext)
                if probe.exists():
                    source = probe
                    extension = probe_ext
                    break
        if not source.exists():
            missing += 1
            continue
        target = source.with_suffix(".pdf")
        if _convert_with_inkscape(inkscape_cmd, source, target):
            converted += 1
            replacements[raw_include] = (
                raw_include[:-4] + ".pdf"
                if raw_include.endswith((".emf", ".wmf", ".svg"))
                else raw_include + ".pdf"
            )
        else:
            failed += 1
    if replacements:
        tex_path.write_text(
            INCLUDE_RE.sub(
                lambda match: match.group(0).replace(
                    match.group(3),
                    replacements.get(match.group(3), match.group(3)),
                    1,
                ),
                content,
            ),
            encoding="utf-8",
        )
    return converted, missing, failed
