"""Normalize explicit \\includegraphics assets for the Pandoc docx route."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

from . import PreprocessorState, registry
from .helpers import find_balanced_brace, find_balanced_bracket

VECTOR_SUFFIXES = {".svg", ".pdf", ".eps"}
DIRECT_IMAGE_SUFFIXES = [
    ".svg",
    ".pdf",
    ".eps",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".tif",
    ".tiff",
]


@registry.register(
    "includegraphics_assets",
    description="Resolve and normalize explicit includegraphics assets for pandoc.",
)
def rewrite_includegraphics_assets(state: PreprocessorState) -> None:
    source_dir = state.path_value("source_dir")
    workspace_root = state.path_value("workspace_root")
    generated_dir = state.path_value("generated_images_dir")
    if source_dir is None or workspace_root is None or generated_dir is None:
        return

    text = state.text
    out: list[str] = []
    i, n = 0, len(text)
    cmd = r"\includegraphics"
    while i < n:
        j = text.find(cmd, i)
        if j == -1:
            out.append(text[i:])
            break
        out.append(text[i:j])
        k = j + len(cmd)
        if k < n and text[k] == "*":
            k += 1
        while k < n and text[k].isspace():
            k += 1
        if k < n and text[k] == "[":
            opt_end = find_balanced_bracket(text, k)
            if opt_end == -1:
                out.append(text[j:])
                break
            k = opt_end + 1
            while k < n and text[k].isspace():
                k += 1
        if k >= n or text[k] != "{":
            out.append(text[j : j + len(cmd)])
            i = j + len(cmd)
            continue
        ref_end = find_balanced_brace(text, k)
        if ref_end == -1:
            out.append(text[j:])
            break

        original_ref = text[k + 1 : ref_end].strip()
        replacement = _resolve_replacement(
            original_ref,
            source_dir=source_dir,
            workspace_root=workspace_root,
            generated_dir=generated_dir,
            metadata=state.metadata,
        )
        if replacement is None:
            out.append(text[j : ref_end + 1])
        else:
            out.append(text[j : k + 1])
            out.append(replacement)
            out.append("}")
        i = ref_end + 1
    state.replace_text("".join(out))


def _resolve_replacement(
    raw_ref: str,
    *,
    source_dir: Path,
    workspace_root: Path,
    generated_dir: Path,
    metadata: dict[str, object],
) -> str | None:
    if not raw_ref or "://" in raw_ref or "\\" in raw_ref or raw_ref.startswith("#"):
        return None
    candidate = _resolve_asset_path(raw_ref, source_dir, workspace_root)
    if candidate is None:
        return None

    if candidate.suffix.lower() not in VECTOR_SUFFIXES:
        return candidate.resolve().as_posix()

    cache = metadata.setdefault("image_conversion_cache", {})
    if not isinstance(cache, dict):
        return candidate.resolve().as_posix()
    cache_key = str(candidate.resolve())
    if cache_key in cache:
        cached = cache[cache_key]
        return str(cached) if isinstance(cached, str) else candidate.resolve().as_posix()

    generated_dir.mkdir(parents=True, exist_ok=True)
    emf_target = _generated_target(candidate, generated_dir, "emf")
    emf_error = _convert_with_inkscape(candidate, emf_target, export_type="emf")
    if emf_error is None:
        replacement = emf_target.resolve().as_posix()
        cache[cache_key] = replacement
        _record_success(
            metadata,
            source=candidate,
            original_ref=raw_ref,
            output=emf_target,
            output_format="emf",
            used_fallback=False,
        )
        return replacement

    if candidate.suffix.lower() in {".pdf", ".eps"}:
        png_target = _generated_target(candidate, generated_dir, "png")
        png_error = _convert_with_inkscape(candidate, png_target, export_type="png", dpi=300)
        if png_error is None:
            replacement = png_target.resolve().as_posix()
            cache[cache_key] = replacement
            _record_success(
                metadata,
                source=candidate,
                original_ref=raw_ref,
                output=png_target,
                output_format="png",
                used_fallback=True,
            )
            _record_fallback(metadata, source=candidate, original_ref=raw_ref, fallback_output=png_target)
            return replacement
        _record_failure(
            metadata,
            source=candidate,
            original_ref=raw_ref,
            reason=f"emf: {emf_error}; png: {png_error}",
        )
    else:
        _record_failure(metadata, source=candidate, original_ref=raw_ref, reason=f"emf: {emf_error}")

    replacement = candidate.resolve().as_posix()
    cache[cache_key] = replacement
    return replacement


def _resolve_asset_path(raw_ref: str, source_dir: Path, workspace_root: Path) -> Path | None:
    raw_path = Path(raw_ref)
    candidates: list[Path] = []
    if raw_path.is_absolute():
        candidates.append(raw_path)
    else:
        candidates.append((source_dir / raw_path).resolve())
        if raw_path.suffix == "":
            for suffix in DIRECT_IMAGE_SUFFIXES:
                candidates.append((source_dir / f"{raw_ref}{suffix}").resolve())
    root = workspace_root.resolve()
    for candidate in candidates:
        if not candidate.exists() or not candidate.is_file():
            continue
        resolved = candidate.resolve()
        if resolved.is_relative_to(root):
            return resolved
    return None


def _generated_target(source: Path, generated_dir: Path, extension: str) -> Path:
    digest = hashlib.sha1(str(source.resolve()).encode("utf-8")).hexdigest()[:10]
    return generated_dir / f"{source.stem}-{digest}.{extension}"


def _convert_with_inkscape(
    source: Path,
    target: Path,
    *,
    export_type: str,
    dpi: int | None = None,
) -> str | None:
    command = [
        "inkscape",
        str(source),
        "--export-type",
        export_type,
        "--export-filename",
        str(target),
    ]
    if source.suffix.lower() == ".pdf":
        command.append("--pdf-poppler")
    if dpi is not None:
        command.extend(["--export-dpi", str(dpi)])
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or exc.stdout or str(exc)).strip()
        return stderr[:500]
    return None


def _record_success(
    metadata: dict[str, object],
    *,
    source: Path,
    original_ref: str,
    output: Path,
    output_format: str,
    used_fallback: bool,
) -> None:
    conversions = metadata.setdefault("image_conversions", [])
    generated = metadata.setdefault("generated_image_files", [])
    if isinstance(conversions, list):
        conversions.append(
            {
                "original_ref": original_ref,
                "source": str(source),
                "output": str(output),
                "output_format": output_format,
                "used_fallback": used_fallback,
            }
        )
    if isinstance(generated, list):
        generated.append(output)


def _record_failure(
    metadata: dict[str, object],
    *,
    source: Path,
    original_ref: str,
    reason: str,
) -> None:
    failures = metadata.setdefault("image_conversion_failures", [])
    if isinstance(failures, list):
        failures.append(
            {
                "original_ref": original_ref,
                "source": str(source),
                "reason": reason,
            }
        )


def _record_fallback(
    metadata: dict[str, object],
    *,
    source: Path,
    original_ref: str,
    fallback_output: Path,
) -> None:
    fallbacks = metadata.setdefault("fallbacks", [])
    if isinstance(fallbacks, list):
        fallbacks.append(
            {
                "original_ref": original_ref,
                "source": str(source),
                "output": str(fallback_output),
                "fallback_format": "png",
                "fallback_dpi": 300,
            }
        )
