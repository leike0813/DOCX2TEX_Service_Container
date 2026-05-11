from __future__ import annotations

import json
import time
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from document_conversion.infrastructure.logging import console, log_line
from document_conversion.infrastructure.state import JobState

from .postprocess import (
    convert_vector_references,
    debug_comment_vsdx_and_normalize,
    release_collect_images_and_normalize,
)


class ArtifactPackager:
    def __init__(self, public_root: Path):
        self.public_root = public_root

    def package(
        self,
        *,
        task_id: str,
        job_state: JobState,
        basename: str,
        work_dir: Path,
        out_tex: Path,
        out_xml: Path,
        debug: bool,
        img_post_proc: bool,
        image_dir: str,
        log_path: Path,
        mtef_source: str | None,
        table_model: str | None,
        fontmaps_dir: Path | None,
        original_filename: str = "",
        display_basename: str = "",
        internal_basename: str = "",
    ) -> Path:
        if img_post_proc and out_tex.exists():
            convert_vector_references(out_tex)
        postprocess_summary = None
        published_basename = display_basename or basename
        result_zip = self.public_root / f"{published_basename}.zip"
        self.public_root.mkdir(parents=True, exist_ok=True)
        manifest_files: list[str] = []
        manifest = {
            "task_id": task_id,
            "debug": debug,
            "start_time": job_state.start_time,
            "end_time": time.time(),
            "files": manifest_files,
            "mtef_source": mtef_source or "",
            "table_model": table_model or "",
            "fontmaps_dir": str(fontmaps_dir) if fontmaps_dir else "",
            "original_filename": original_filename,
            "display_basename": published_basename,
            "internal_basename": internal_basename or basename,
            "ole_binary_refs_commented": 0,
            "ole_binary_ref_paths": [],
            "ole_binary_assets_skipped": 0,
            "ole_binary_asset_paths": [],
        }
        log_line(log_path, f"packaging -> {result_zip}")
        console(f"task={task_id} stage=packaging zip={result_zip}")
        with ZipFile(result_zip, "w", ZIP_DEFLATED) as zf:
            if debug:
                try:
                    postprocess_summary = debug_comment_vsdx_and_normalize(out_tex)
                except Exception:
                    pass
                for path, arcname in [
                    (out_tex, f"{published_basename}.tex"),
                    (out_xml, f"{published_basename}.xml"),
                    (work_dir / f"{basename}.csv", f"{published_basename}.csv"),
                ]:
                    if path.exists():
                        zf.write(path, arcname=arcname)
                        manifest_files.append(arcname)
                for directory_name in [f"{basename}.debug", f"{basename}.docx.tmp"]:
                    directory = work_dir / directory_name
                    if directory.exists():
                        for child in directory.rglob("*"):
                            if child.is_file():
                                arcname = f"{directory.name}/{child.relative_to(directory)}"
                                zf.write(child, arcname=arcname)
                                manifest_files.append(arcname)
                if log_path.exists():
                    zf.write(log_path, arcname=f"logs/{log_path.name}")
                    manifest_files.append(f"logs/{log_path.name}")
                for path, arcname in [
                    (work_dir / "custom-evolve-effective.xsl", "xsl/custom-evolve-effective.xsl"),
                    (work_dir / "stylemap_manifest.json", "stylemap_manifest.json"),
                ]:
                    if path.exists():
                        zf.write(path, arcname=arcname)
                        manifest_files.append(arcname)
            else:
                image_dir_path = work_dir / image_dir
                try:
                    postprocess_summary = release_collect_images_and_normalize(
                        out_tex,
                        image_dir_path,
                        image_alias=image_dir,
                    )
                except Exception:
                    pass
                if out_tex.exists():
                    arcname = f"{published_basename}.tex"
                    zf.write(out_tex, arcname=arcname)
                    manifest_files.append(arcname)
                if image_dir_path.exists():
                    for child in image_dir_path.rglob("*"):
                        if child.is_file():
                            arcname = f"{image_dir}/{child.relative_to(image_dir_path)}"
                            zf.write(child, arcname=arcname)
                            manifest_files.append(arcname)
            if postprocess_summary is not None:
                manifest["ole_binary_refs_commented"] = (
                    postprocess_summary.commented_ole_binary_refs
                )
                manifest["ole_binary_ref_paths"] = postprocess_summary.ole_binary_ref_paths
                manifest["ole_binary_assets_skipped"] = (
                    postprocess_summary.skipped_ole_binary_assets
                )
                manifest["ole_binary_asset_paths"] = postprocess_summary.ole_binary_asset_paths
            zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        if not debug and not out_tex.exists():
            raise RuntimeError("no output produced")
        return result_zip
