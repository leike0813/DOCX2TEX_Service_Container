from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from document_conversion.domain import (
    ConversionJob,
    ConversionPath,
    ConversionRequest,
    DocumentFormat,
    InputSource,
    InputSourceKind,
)
from document_conversion.infrastructure.task_metadata import read_task_metadata


@dataclass
class PlatformTaskSubmission:
    source_format: str
    target_format: str
    profile_id: str | None = None
    file: Any | None = None
    url: str | None = None
    debug: bool = False
    img_post_proc: bool = True
    conf: Any | None = None
    custom_xsl: Any | None = None
    custom_xsl_preset: str | None = None
    custom_evolve: Any | None = None
    style_map: str | None = None
    math_type_source: str | None = None
    table_model: str | None = None
    fontmaps_zip: Any | None = None
    image_dir: str | None = None
    main_tex: str | None = None
    reference_doc_id: str | None = None
    numbering_metadata_id: str | None = None
    lua_filter_ids: str | None = None
    exec_filter_ids: str | None = None
    top_level_division: str | None = None
    citeproc: bool = False
    csl_id: str | None = None
    bibliography_paths: str | None = None
    options: dict[str, Any] = field(default_factory=dict)


class PlatformService:
    def __init__(self, runtime: Any):
        self.runtime = runtime

    def list_capabilities(self) -> dict[str, Any]:
        return self.runtime.capabilities_payload()

    def list_profiles(self) -> dict[str, Any]:
        return self.runtime.profiles_payload()

    async def submit_task(self, submission: PlatformTaskSubmission) -> dict[str, Any]:
        request = self._build_request(submission)
        try:
            profile = self.runtime.registry.resolve_profile(request.path.id, request.profile_id)
        except KeyError as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown profile for path {request.path.id}: {request.profile_id}",
            ) from exc
        engine = self.runtime.registry.get(profile.engine_id)
        return await engine.submit(submission, self.runtime, request, profile)

    def get_task(self, task_id: str) -> ConversionJob:
        job = self.runtime.jobs.get(task_id)
        return ConversionJob(
            task_id=job.task_id,
            state=job.state,
            err_msg=job.err_msg,
            start_time=job.start_time,
            end_time=job.end_time,
            debug=job.debug,
            work_dir=job.work_dir,
        )

    def result_path(self, task_id: str) -> tuple[ConversionJob, Path]:
        job = self.get_task(task_id)
        work_dir = Path(job.work_dir)
        metadata = read_task_metadata(work_dir)
        result_name = str(metadata.get("result_name", "")).strip()
        if result_name:
            return job, self.runtime.cfg.public_root / result_name
        tex_files = list(work_dir.glob("*.tex"))
        basename = tex_files[0].stem if tex_files else work_dir.name
        return job, self.runtime.cfg.public_root / f"{basename}.zip"

    def _build_request(self, submission: PlatformTaskSubmission) -> ConversionRequest:
        try:
            source_format = DocumentFormat(submission.source_format)
            target_format = DocumentFormat(submission.target_format)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        if not submission.profile_id:
            raise HTTPException(status_code=400, detail="profile_id is required")

        has_file = submission.file is not None
        has_url = bool(submission.url)
        if (not has_file and not has_url) or (has_file and has_url):
            raise HTTPException(status_code=400, detail="Provide exactly one of file or url")

        input_source = InputSource(
            kind=InputSourceKind.FILE if has_file else InputSourceKind.URL,
            filename=getattr(submission.file, "filename", None),
            url=submission.url,
        )
        path = ConversionPath(source_format=source_format, target_format=target_format)
        return ConversionRequest(
            path=path,
            input_source=input_source,
            profile_id=submission.profile_id,
            debug=submission.debug,
            options={
                "img_post_proc": submission.img_post_proc,
                "custom_xsl_preset": submission.custom_xsl_preset,
                "math_type_source": submission.math_type_source,
                "table_model": submission.table_model,
                "image_dir": submission.image_dir,
                "main_tex": submission.main_tex,
                "reference_doc_id": submission.reference_doc_id,
                "numbering_metadata_id": submission.numbering_metadata_id,
                "lua_filter_ids": submission.lua_filter_ids,
                "exec_filter_ids": submission.exec_filter_ids,
                "top_level_division": submission.top_level_division,
                "citeproc": submission.citeproc,
                "csl_id": submission.csl_id,
                "bibliography_paths": submission.bibliography_paths,
            },
        )
