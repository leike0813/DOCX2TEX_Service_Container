from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from fastapi import HTTPException, UploadFile

from document_conversion.domain import CapabilityCell, ConversionEngine, ConversionProfile, DocumentFormat
from document_conversion.infrastructure.process import download_to
from document_conversion.infrastructure.storage import safe_name, write_bytes
from document_conversion.infrastructure.task_metadata import write_task_metadata
from engines.docx2tex_engine.convert import compute_cache_key, rewrite_conf_imports_to_default
from engines.docx2tex_engine.filenames import sanitize_filename
from engines.docx2tex_engine.presets import (
    CUSTOM_XSL_PRESETS,
    resolve_conf_preset,
    resolve_custom_xsl_preset,
)
from engines.docx2tex_engine.stylemap import prepare_effective_xsls
from engines.docx2tex_engine.profiles import DOCX2TEX_PROFILES


@dataclass
class PreparedSubmission:
    task_id: str
    input_docx: Path
    source_kind: str
    source_value: str
    conf_path: Optional[Path]
    custom_xsl_path: Optional[Path]
    custom_evolve_path: Optional[Path]
    fontmaps_zip_path: Optional[Path]
    image_dir: str


class Docx2TexEngine(ConversionEngine):
    engine_id = "docx2tex"

    def capability_cells(self) -> list[CapabilityCell]:
        return [
            CapabilityCell(
                path_id="docx_to_latex",
                engine_id=self.engine_id,
                source_format=DocumentFormat.DOCX,
                target_format=DocumentFormat.LATEX,
                status="implemented",
                description="Primary high-quality docx to latex conversion via docx2tex.",
            )
        ]

    def profiles(self) -> list[ConversionProfile]:
        return DOCX2TEX_PROFILES

    async def submit(
        self,
        submission: Any,
        runtime: Any,
        request: Any,
        profile: ConversionProfile,
    ) -> dict[str, Any]:
        if request.path.id != "docx_to_latex":
            raise HTTPException(status_code=400, detail="docx2tex only supports docx -> latex")

        prepared = await self._prepare_submission(submission, runtime, profile)
        cache_key = compute_cache_key(
            prepared.input_docx,
            prepared.conf_path or self._default_conf_path(runtime),
            prepared.custom_xsl_path,
            prepared.custom_evolve_path,
            submission.math_type_source,
            submission.table_model,
            prepared.fontmaps_zip_path,
        )

        cache_status = "MISS"
        row = runtime.cache.get(cache_key)
        if row and int(row.get("available", 0)) == 1:
            cache_status = "HIT"
        elif row and int(row.get("available", 0)) == 0:
            cache_status = "BUILDING"

        runtime.jobs.submit(
            task_id=prepared.task_id,
            source_kind=prepared.source_kind,
            source_value=prepared.source_value,
            debug=submission.debug,
            img_post_proc=submission.img_post_proc,
            conf_file=prepared.conf_path,
            custom_xsl=prepared.custom_xsl_path,
            custom_evolve=prepared.custom_evolve_path,
            mtef_source=submission.math_type_source,
            table_model=submission.table_model,
            fontmaps_dir=None,
            fontmaps_zip=prepared.fontmaps_zip_path,
            job_cache_key=cache_key,
            no_cache=False,
            image_dir=prepared.image_dir,
        )
        return {
            "task_id": prepared.task_id,
            "cache_key": cache_key,
            "cache_status": cache_status,
            "path_id": request.path.id,
            "engine_id": self.engine_id,
            "profile_id": profile.id,
        }

    async def _prepare_submission(
        self,
        submission: Any,
        runtime: Any,
        profile: ConversionProfile,
    ) -> PreparedSubmission:
        has_file = submission.file is not None
        has_url = bool(submission.url)
        if (not has_file and not has_url) or (has_file and has_url):
            raise HTTPException(status_code=400, detail="Provide exactly one of file or url")

        self._validate_conflicts(submission)

        job = runtime.jobs.create(debug=submission.debug, img_post_proc=submission.img_post_proc)
        work = Path(job.work_dir)

        if submission.file is not None:
            name = safe_name(getattr(submission.file, "filename", None) or "document.docx")
            if not name.lower().endswith(".docx"):
                name = f"{name}.docx"
            input_docx = work / name
            await self._write_upload_stream(submission.file, input_docx, runtime.cfg.max_upload_bytes)
            input_docx = self._sanitize_uploaded_path(input_docx)
            source_kind = "file"
            source_value = input_docx.name
        else:
            name = self._safe_filename_from_url(submission.url or "")
            input_docx = work / name
            download_to(input_docx, submission.url or "")
            input_docx = self._sanitize_uploaded_path(input_docx)
            source_kind = "url"
            source_value = input_docx.name

        conf_path, xsl_path, evolve_path, fontmaps_zip_path = await self._prepare_optional_inputs(
            work=work,
            runtime=runtime,
            conf=submission.conf,
            profile=profile,
            custom_xsl=submission.custom_xsl,
            custom_xsl_preset=submission.custom_xsl_preset,
            custom_evolve=submission.custom_evolve,
            style_map=submission.style_map,
            fontmaps_zip=submission.fontmaps_zip,
        )
        write_task_metadata(
            work,
            {
                "path_id": "docx_to_latex",
                "engine_id": self.engine_id,
                "profile_id": profile.id,
                "result_name": f"{input_docx.stem}.zip",
            },
        )
        return PreparedSubmission(
            task_id=job.task_id,
            input_docx=input_docx,
            source_kind=source_kind,
            source_value=source_value,
            conf_path=conf_path,
            custom_xsl_path=xsl_path,
            custom_evolve_path=evolve_path,
            fontmaps_zip_path=fontmaps_zip_path,
            image_dir=self._resolve_image_dir(submission.image_dir),
        )

    async def _prepare_optional_inputs(
        self,
        *,
        work: Path,
        runtime: Any,
        conf: UploadFile | None,
        profile: ConversionProfile,
        custom_xsl: UploadFile | None,
        custom_xsl_preset: str | None,
        custom_evolve: UploadFile | None,
        style_map: str | None,
        fontmaps_zip: UploadFile | None,
    ) -> tuple[Optional[Path], Optional[Path], Optional[Path], Optional[Path]]:
        conf_path = await self._prepare_effective_conf(
            work=work,
            runtime=runtime,
            conf=conf,
            profile=profile,
        )

        xsl_path: Optional[Path] = None
        if custom_xsl is not None:
            xsl_path = work / "custom.xsl"
            write_bytes(xsl_path, await custom_xsl.read())
            xsl_path = self._sanitize_uploaded_path(xsl_path)
        elif custom_xsl_preset:
            xsl_path = self._resolve_custom_xsl_preset_or_400(custom_xsl_preset)

        evolve_path: Optional[Path] = None
        if custom_evolve is not None:
            evolve_path = work / "custom-evolve-hub-driver.xsl"
            write_bytes(evolve_path, await custom_evolve.read())
            evolve_path = self._sanitize_uploaded_path(evolve_path)

        fontmaps_zip_path: Optional[Path] = None
        if fontmaps_zip is not None:
            fontmaps_zip_path = work / "fontmaps.zip"
            write_bytes(fontmaps_zip_path, await fontmaps_zip.read())

        try:
            if style_map and style_map.strip():
                confs = [
                    path
                    for path in [self._default_conf_path(runtime), conf_path]
                    if path is not None
                ]
                effective_evolve, _, _ = prepare_effective_xsls(style_map, confs, evolve_path, work)
                if effective_evolve:
                    evolve_path = effective_evolve
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"StyleMap processing failed: {exc}") from exc

        return conf_path, xsl_path, evolve_path, fontmaps_zip_path

    async def _prepare_effective_conf(
        self,
        *,
        work: Path,
        runtime: Any,
        conf: UploadFile | None,
        profile: ConversionProfile,
    ) -> Path:
        default_conf = self._default_conf_path(runtime)
        effective_conf = work / "effective-conf.xml"

        if conf is not None:
            write_bytes(effective_conf, await conf.read())
        else:
            preset_path = self._resolve_conf_profile_or_400(profile)
            shutil.copy2(preset_path, effective_conf)

        try:
            rewrite_conf_imports_to_default(effective_conf, default_conf)
        except Exception:
            pass
        return effective_conf

    def _validate_conflicts(self, submission: Any) -> None:
        if submission.conf is not None and submission.profile_id:
            raise HTTPException(status_code=400, detail="conf and profile_id cannot be used together")
        if submission.custom_xsl is not None and submission.custom_xsl_preset:
            raise HTTPException(
                status_code=400,
                detail="custom_xsl and custom_xsl_preset cannot be used together",
            )

    def _default_conf_path(self, runtime: Any) -> Path:
        return runtime.cfg.docx2tex_home / "conf" / "conf.xml"

    @staticmethod
    def _sanitize_uploaded_path(path: Path) -> Path:
        safe = sanitize_filename(path.name)
        if safe == path.name:
            return path
        new_path = path.with_name(safe)
        path.replace(new_path)
        return new_path

    @staticmethod
    def _resolve_image_dir(image_dir: str | None) -> str:
        cleaned = sanitize_filename(image_dir or "image")
        return cleaned or "image"

    @staticmethod
    async def _write_upload_stream(upload: UploadFile, dest: Path, max_bytes: int = 0) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        total = 0
        with open(dest, "wb") as out:
            while True:
                chunk = await upload.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if max_bytes and total > max_bytes:
                    out.close()
                    try:
                        dest.unlink(missing_ok=True)  # type: ignore[arg-type]
                    except Exception:
                        pass
                    raise HTTPException(status_code=413, detail="uploaded file exceeds size limit")
                out.write(chunk)
        try:
            await upload.close()
        except Exception:
            pass

    @staticmethod
    def _safe_filename_from_url(url: str) -> str:
        try:
            from urllib.parse import urlparse

            parsed = urlparse(url)
            name = Path(parsed.path).name
            if not name:
                return "document.docx"
            if not name.lower().endswith(".docx"):
                name = f"{name}.docx"
            return safe_name(name)
        except Exception:
            return "document.docx"

    @staticmethod
    def _resolve_conf_profile_or_400(profile: ConversionProfile) -> Path:
        preset_id = str(profile.engine_options.get("conf_preset_id", "")).strip()
        path = resolve_conf_preset(preset_id)
        if path is None or not path.exists():
            raise HTTPException(status_code=400, detail=f"Unsupported profile_id: {profile.id}")
        return path

    @staticmethod
    def _resolve_custom_xsl_preset_or_400(preset_id: str) -> Optional[Path]:
        if preset_id == "none":
            return None
        if preset_id not in CUSTOM_XSL_PRESETS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported custom_xsl_preset: {preset_id}",
            )
        path = resolve_custom_xsl_preset(preset_id)
        if path is None or not path.exists():
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported custom_xsl_preset: {preset_id}",
            )
        return path
