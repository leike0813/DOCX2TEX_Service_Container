from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import HTTPException

from document_conversion.domain import CapabilityCell, ConversionEngine, ConversionProfile, DocumentFormat
from document_conversion.infrastructure.logging import log_line
from document_conversion.infrastructure.storage import safe_name, write_bytes
from document_conversion.infrastructure.task_metadata import write_task_metadata
from engines.pandoc_engine.config import TemplateDetector, TemplateRegistry
from engines.pandoc_engine.orchestrator import PipelineContext, PipelineOrchestrator
from engines.pandoc_engine.resources import (
    available_exec_filter,
    auto_reference_doc_id,
    csl_path,
    default_latex_to_docx_options,
    exec_filter_binary,
    lua_filter_path,
    metadata_path,
    reference_doc_path,
)

PANDOC_PROFILES: list[ConversionProfile] = [
    ConversionProfile(
        id="docx_to_latex/pandoc-default",
        label="Pandoc Default",
        path_id="docx_to_latex",
        engine_id="pandoc",
        description="Fallback docx to latex conversion via pandoc.",
    ),
    ConversionProfile(
        id="latex_to_docx/pandoc-auto",
        label="Pandoc Auto",
        path_id="latex_to_docx",
        engine_id="pandoc",
        description="Auto-detect the best template for a latex workspace.",
    ),
    ConversionProfile(
        id="latex_to_docx/pandoc-ctexart",
        label="Pandoc CTeX Art",
        path_id="latex_to_docx",
        engine_id="pandoc",
        description="Force the ctexart template.",
        engine_options={"template_name": "ctexart"},
    ),
    ConversionProfile(
        id="latex_to_docx/pandoc-ctexbook",
        label="Pandoc CTeX Book",
        path_id="latex_to_docx",
        engine_id="pandoc",
        description="Force the ctexbook template.",
        engine_options={"template_name": "ctexbook"},
    ),
    ConversionProfile(
        id="latex_to_docx/pandoc-elsarticle",
        label="Pandoc Elsevier Article",
        path_id="latex_to_docx",
        engine_id="pandoc",
        description="Force the elsarticle template.",
        engine_options={"template_name": "elsarticle"},
    ),
    ConversionProfile(
        id="latex_to_markdown/pandoc-default",
        label="Pandoc Markdown",
        path_id="latex_to_markdown",
        engine_id="pandoc",
        description="Reserved future profile for latex to markdown.",
    ),
]


class PandocEngine(ConversionEngine):
    engine_id = "pandoc"

    def capability_cells(self) -> list[CapabilityCell]:
        return [
            CapabilityCell(
                path_id="docx_to_latex",
                engine_id=self.engine_id,
                source_format=DocumentFormat.DOCX,
                target_format=DocumentFormat.LATEX,
                status="implemented",
                description="Fallback docx to latex conversion via pandoc.",
            ),
            CapabilityCell(
                path_id="latex_to_docx",
                engine_id=self.engine_id,
                source_format=DocumentFormat.LATEX,
                target_format=DocumentFormat.DOCX,
                status="implemented",
                description="Latex workspace to docx conversion via pandoc.",
            ),
            CapabilityCell(
                path_id="latex_to_markdown",
                engine_id=self.engine_id,
                source_format=DocumentFormat.LATEX,
                target_format=DocumentFormat.MARKDOWN,
                status="planned",
                description="Reserved future path for latex to markdown.",
            ),
        ]

    def profiles(self) -> list[ConversionProfile]:
        return PANDOC_PROFILES

    async def submit(self, submission, runtime, request, profile: ConversionProfile) -> dict[str, object]:
        if request.path.id == "docx_to_latex":
            return await self._submit_docx_to_latex(submission, runtime, profile)
        if request.path.id == "latex_to_docx":
            return await self._submit_latex_to_docx(submission, runtime, profile)
        raise HTTPException(
            status_code=501,
            detail=f"{request.path.id}@pandoc is planned but not implemented yet",
        )

    async def _submit_docx_to_latex(self, submission, runtime, profile: ConversionProfile) -> dict[str, object]:
        if submission.url:
            raise HTTPException(status_code=400, detail="pandoc docx->latex currently requires file upload")
        if submission.file is None:
            raise HTTPException(status_code=400, detail="file upload is required")
        filename = safe_name(getattr(submission.file, "filename", None) or "document.docx")
        if not filename.lower().endswith(".docx"):
            raise HTTPException(status_code=400, detail="pandoc docx->latex requires a .docx upload")
        job = runtime.jobs.create(debug=submission.debug, img_post_proc=False)
        work_dir = Path(job.work_dir)
        input_path = work_dir / filename
        write_bytes(input_path, await submission.file.read())
        write_task_metadata(
            work_dir,
            {
                "path_id": "docx_to_latex",
                "engine_id": self.engine_id,
                "profile_id": profile.id,
                "result_name": f"{job.task_id}.zip",
            },
        )
        runtime.jobs.pool.submit(
            self._run_docx_to_latex_job,
            runtime,
            job.task_id,
            input_path,
            submission.debug,
        )
        return {
            "task_id": job.task_id,
            "cache_status": "BYPASS",
            "path_id": "docx_to_latex",
            "engine_id": self.engine_id,
            "profile_id": profile.id,
        }

    async def _submit_latex_to_docx(self, submission, runtime, profile: ConversionProfile) -> dict[str, object]:
        if submission.url:
            raise HTTPException(status_code=400, detail="latex->docx requires a workspace zip upload")
        if submission.file is None:
            raise HTTPException(status_code=400, detail="workspace zip upload is required")
        filename = safe_name(getattr(submission.file, "filename", None) or "workspace.zip")
        if not filename.lower().endswith(".zip"):
            raise HTTPException(status_code=400, detail="latex->docx requires a .zip upload")
        job = runtime.jobs.create(debug=submission.debug, img_post_proc=False)
        work_dir = Path(job.work_dir)
        workspace_zip = work_dir / filename
        write_bytes(workspace_zip, await submission.file.read())
        write_task_metadata(
            work_dir,
            {
                "path_id": "latex_to_docx",
                "engine_id": self.engine_id,
                "profile_id": profile.id,
                "result_name": f"{job.task_id}.zip",
            },
        )
        runtime.jobs.pool.submit(
            self._run_latex_to_docx_job,
            runtime,
            job.task_id,
            workspace_zip,
            submission.main_tex,
            profile,
            submission.debug,
            submission.options,
        )
        return {
            "task_id": job.task_id,
            "cache_status": "BYPASS",
            "path_id": "latex_to_docx",
            "engine_id": self.engine_id,
            "profile_id": profile.id,
        }

    def _run_docx_to_latex_job(self, runtime, task_id: str, input_path: Path, debug: bool) -> None:
        work_dir = input_path.parent
        log_path = runtime.cfg.log_dir / f"{task_id}.log"
        output_tex = work_dir / f"{input_path.stem}.tex"
        try:
            runtime.jobs.set_state(task_id, "running")
            runtime.jobs.set_state(task_id, "converting")
            command = ["pandoc", str(input_path), "-f", "docx", "-t", "latex", "-o", str(output_tex)]
            log_path.write_text(" ".join(command) + "\n", encoding="utf-8")
            subprocess.run(command, check=True)
            runtime.jobs.set_state(task_id, "packaging")
            result_zip = runtime.cfg.public_root / f"{task_id}.zip"
            manifest = {
                "task_id": task_id,
                "path_id": "docx_to_latex",
                "engine_id": self.engine_id,
                "files": [output_tex.name],
                "debug": debug,
                "command": command,
            }
            with ZipFile(result_zip, "w", ZIP_DEFLATED) as archive:
                archive.write(output_tex, arcname=output_tex.name)
                if debug:
                    archive.write(input_path, arcname=input_path.name)
                    if log_path.exists():
                        archive.write(log_path, arcname=f"logs/{log_path.name}")
                archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
            runtime.jobs.set_state(task_id, "done")
        except Exception as exc:
            log_line(log_path, f"pandoc_docx_to_latex_failed: {exc}")
            runtime.jobs.set_state(task_id, "failed", str(exc))

    def _run_latex_to_docx_job(
        self,
        runtime,
        task_id: str,
        workspace_zip: Path,
        main_tex: str | None,
        profile: ConversionProfile,
        debug: bool,
        submission_options: dict[str, Any],
    ) -> None:
        work_dir = workspace_zip.parent
        extract_dir = work_dir / "workspace"
        log_path = runtime.cfg.log_dir / f"{task_id}.log"
        output_docx = work_dir / "result.docx"
        try:
            runtime.jobs.set_state(task_id, "running")
            extract_dir.mkdir(parents=True, exist_ok=True)
            with ZipFile(workspace_zip, "r") as archive:
                archive.extractall(extract_dir)
            runtime.jobs.set_state(task_id, "converting")
            entry_tex = self._resolve_main_tex(extract_dir, main_tex)
            registry = TemplateRegistry(Path(__file__).resolve().parent / "assets" / "templates")
            orchestrator = PipelineOrchestrator(registry)
            resolved = self._resolve_latex_to_docx_options(
                runtime,
                extract_dir,
                profile,
                entry_tex,
                submission_options,
            )
            pipeline_ctx = PipelineContext(
                source_path=entry_tex,
                output_path=output_docx,
                workdir=work_dir / "pandoc-work",
                workspace_root=extract_dir,
                template_name=profile.engine_options.get("template_name"),
                dry_run=False,
                reference_doc=resolved["reference_doc"],
                metadata_files=resolved["metadata_files"],
                lua_filters=resolved["lua_filters"],
                exec_filters=resolved["exec_filters"],
                top_level_division=resolved["top_level_division"],
                citeproc=resolved["citeproc"],
                csl=resolved["csl"],
                bibliography_paths=resolved["bibliography_paths"],
            )
            plan = orchestrator.run(pipeline_ctx)
            log_path.write_text(" ".join(plan.pandoc_command) + "\n", encoding="utf-8")
            for item in plan.image_conversions:
                log_line(log_path, f"pandoc_image_conversion: {item}")
            for item in plan.fallbacks:
                log_line(log_path, f"pandoc_image_fallback: {item}")
            for item in plan.image_conversion_failures:
                log_line(log_path, f"pandoc_image_conversion_failed: {item}")
            runtime.jobs.set_state(task_id, "packaging")
            result_zip = runtime.cfg.public_root / f"{task_id}.zip"
            manifest_files = [output_docx.name]
            with ZipFile(result_zip, "w", ZIP_DEFLATED) as archive:
                archive.write(output_docx, arcname=output_docx.name)
                if debug:
                    archive.write(plan.intermediate_tex, arcname=plan.intermediate_tex.name)
                    archive.write(workspace_zip, arcname=workspace_zip.name)
                    for generated_image in plan.generated_image_files:
                        archive.write(
                            generated_image,
                            arcname=f"generated-images/{generated_image.name}",
                        )
                    if log_path.exists():
                        archive.write(log_path, arcname=f"logs/{log_path.name}")
                    manifest_files.extend(
                        [
                            plan.intermediate_tex.name,
                            workspace_zip.name,
                            f"logs/{log_path.name}",
                        ]
                    )
                    manifest_files.extend(
                        [f"generated-images/{path.name}" for path in plan.generated_image_files]
                    )
                archive.writestr(
                    "manifest.json",
                    json.dumps(
                        {
                            "task_id": task_id,
                            "path_id": "latex_to_docx",
                            "engine_id": self.engine_id,
                            "profile_id": profile.id,
                            "template": plan.template.name,
                            "executed_preprocessors": plan.executed_preprocessors,
                            "reference_doc": str(plan.resolved_reference_doc) if plan.resolved_reference_doc else "",
                            "metadata_files": [str(path) for path in plan.resolved_metadata_files],
                            "lua_filters": [str(path) for path in plan.resolved_lua_filters],
                            "exec_filters": plan.resolved_exec_filters,
                            "top_level_division": plan.resolved_top_level_division or "",
                            "citeproc": plan.citeproc_enabled,
                            "csl": str(plan.resolved_csl) if plan.resolved_csl else "",
                            "bibliography_paths": [str(path) for path in plan.resolved_bibliography],
                            "image_conversions": plan.image_conversions,
                            "image_conversion_failures": plan.image_conversion_failures,
                            "fallbacks": plan.fallbacks,
                            "command": plan.pandoc_command,
                            "files": manifest_files,
                            "debug": debug,
                        },
                        ensure_ascii=False,
                        indent=2,
                    ),
                )
            runtime.jobs.set_state(task_id, "done")
        except Exception as exc:
            runtime.jobs.set_state(task_id, "failed", str(exc))
            log_line(log_path, f"pandoc_latex_to_docx_failed: {exc}")
        finally:
            shutil.rmtree(extract_dir, ignore_errors=True)

    @staticmethod
    def _resolve_main_tex(workspace_dir: Path, main_tex: str | None) -> Path:
        if main_tex:
            candidate = (workspace_dir / main_tex).resolve()
            if workspace_dir.resolve() not in candidate.parents and candidate != workspace_dir.resolve():
                raise RuntimeError("main_tex must stay inside the uploaded workspace")
            if not candidate.exists():
                raise RuntimeError(f"main_tex not found: {main_tex}")
            return candidate
        for name in ["main.tex", "index.tex"]:
            candidate = workspace_dir / name
            if candidate.exists():
                return candidate
        tex_files = sorted(workspace_dir.rglob("*.tex"))
        if len(tex_files) == 1:
            return tex_files[0]
        raise RuntimeError("Unable to resolve main tex entrypoint from workspace zip")

    def _resolve_latex_to_docx_options(
        self,
        runtime,
        workspace_dir: Path,
        profile: ConversionProfile,
        entry_tex: Path,
        submission_options: dict[str, Any],
    ) -> dict[str, Any]:
        defaults = default_latex_to_docx_options(profile.id)
        merged = dict(defaults)
        for key in [
            "reference_doc_id",
            "numbering_metadata_id",
            "top_level_division",
            "csl_id",
        ]:
            value = submission_options.get(key)
            if isinstance(value, str) and value.strip():
                merged[key] = value.strip()
        for key in ["citeproc"]:
            if key in submission_options:
                merged[key] = bool(submission_options[key])

        for key in ["lua_filter_ids", "exec_filter_ids", "bibliography_paths"]:
            raw = submission_options.get(key)
            if isinstance(raw, list):
                merged[key] = raw
            elif raw:
                merged[key] = self._parse_json_list(raw, key)

        # Auto profile chooses defaults after real template detection.
        if profile.id == "latex_to_docx/pandoc-auto":
            registry = TemplateRegistry(Path(__file__).resolve().parent / "assets" / "templates")
            detected = TemplateDetector(registry).guess(entry_tex)
            if merged.get("reference_doc_id") == defaults.get("reference_doc_id"):
                merged["reference_doc_id"] = auto_reference_doc_id(detected.name)
            if merged.get("top_level_division") == defaults.get("top_level_division"):
                merged["top_level_division"] = "chapter" if detected.name == "ctexbook" else "section"
            if merged.get("numbering_metadata_id") == defaults.get("numbering_metadata_id") and detected.name == "ctexbook":
                merged["numbering_metadata_id"] = "zh-book"
        reference_id = str(merged.get("reference_doc_id", "")).strip()
        metadata_id = str(merged.get("numbering_metadata_id", "")).strip()
        top_level_division = str(merged.get("top_level_division", "")).strip() or None
        citeproc = bool(merged.get("citeproc", False))
        csl_id = str(merged.get("csl_id", "")).strip()
        lua_filter_ids_raw = merged.get("lua_filter_ids", [])
        exec_filter_ids_raw = merged.get("exec_filter_ids", [])
        bibliography_paths_raw = merged.get("bibliography_paths", [])
        lua_filter_ids = (
            [str(item) for item in lua_filter_ids_raw]
            if isinstance(lua_filter_ids_raw, list)
            else []
        )
        exec_filter_ids = (
            [str(item) for item in exec_filter_ids_raw]
            if isinstance(exec_filter_ids_raw, list)
            else []
        )
        bibliography_paths = (
            [str(item) for item in bibliography_paths_raw]
            if isinstance(bibliography_paths_raw, list)
            else []
        )

        if top_level_division not in {None, "section", "chapter", "part"}:
            raise RuntimeError(f"Unsupported top_level_division: {top_level_division}")

        reference_doc = reference_doc_path(reference_id, runtime.cfg.data_root.parent) if reference_id else None
        metadata_files = [metadata_path(metadata_id)] if metadata_id else []
        lua_filters = [lua_filter_path(item) for item in lua_filter_ids]
        exec_filters: list[str] = []
        for item in exec_filter_ids:
            if not available_exec_filter(item):
                raise RuntimeError(f"Required executable filter is missing: {item}")
            exec_filters.append(exec_filter_binary(item))

        csl = csl_path(csl_id) if csl_id else None
        bibliography = self._resolve_bibliography_paths(workspace_dir, bibliography_paths, citeproc)
        if csl is not None and not citeproc:
            csl = None

        return {
            "reference_doc": reference_doc,
            "metadata_files": metadata_files,
            "lua_filters": lua_filters,
            "exec_filters": exec_filters,
            "top_level_division": top_level_division,
            "citeproc": citeproc,
            "csl": csl,
            "bibliography_paths": bibliography,
        }

    @staticmethod
    def _parse_json_list(raw: Any, field_name: str) -> list[str]:
        if raw is None or raw == "":
            return []
        if not isinstance(raw, str):
            raise RuntimeError(f"{field_name} must be a JSON string array")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"{field_name} must be a valid JSON array") from exc
        if not isinstance(payload, list) or any(not isinstance(item, str) for item in payload):
            raise RuntimeError(f"{field_name} must be a JSON string array")
        return [item.strip() for item in payload if item.strip()]

    @staticmethod
    def _resolve_bibliography_paths(
        workspace_dir: Path,
        requested: list[str],
        citeproc: bool,
    ) -> list[Path]:
        if not citeproc:
            return []
        if requested:
            result: list[Path] = []
            root = workspace_dir.resolve()
            for item in requested:
                candidate = (workspace_dir / item).resolve()
                if root not in candidate.parents and candidate != root:
                    raise RuntimeError(f"bibliography path escapes workspace: {item}")
                if not candidate.exists():
                    raise RuntimeError(f"bibliography not found: {item}")
                result.append(candidate)
            return result
        return sorted(workspace_dir.rglob("*.bib"))
