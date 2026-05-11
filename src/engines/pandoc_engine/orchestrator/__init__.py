"""High-level orchestration for the Pandoc engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from engines.pandoc_engine.config import TemplateConfig, TemplateConfigError, TemplateDetector, TemplateRegistry
from engines.pandoc_engine.postprocessors import registry as postprocessor_registry
from engines.pandoc_engine.preprocessors import run_preprocessors
from engines.pandoc_engine.runner import PandocRunner


@dataclass
class PipelineContext:
    source_path: Path
    output_path: Path
    workdir: Path
    workspace_root: Path | None = None
    template_name: str | None = None
    dry_run: bool = False
    reference_doc: Path | None = None
    metadata_files: list[Path] = field(default_factory=list)
    lua_filters: list[Path] = field(default_factory=list)
    exec_filters: list[str] = field(default_factory=list)
    top_level_division: str | None = None
    citeproc: bool = False
    csl: Path | None = None
    bibliography_paths: list[Path] = field(default_factory=list)


@dataclass
class PipelinePlan:
    template: TemplateConfig
    preprocessors: list[str]
    filters: list[str]
    postprocessors: list[str]
    pandoc_command: list[str]
    intermediate_tex: Path
    resolved_reference_doc: Path | None = None
    resolved_metadata_files: list[Path] = field(default_factory=list)
    resolved_lua_filters: list[Path] = field(default_factory=list)
    resolved_exec_filters: list[str] = field(default_factory=list)
    resolved_csl: Path | None = None
    resolved_bibliography: list[Path] = field(default_factory=list)
    resolved_top_level_division: str | None = None
    citeproc_enabled: bool = False
    executed_preprocessors: list[str] = field(default_factory=list)
    image_conversions: list[dict[str, object]] = field(default_factory=list)
    image_conversion_failures: list[dict[str, object]] = field(default_factory=list)
    fallbacks: list[dict[str, object]] = field(default_factory=list)
    generated_image_files: list[Path] = field(default_factory=list)


class PipelineOrchestrator:
    def __init__(self, registry: TemplateRegistry, runner: PandocRunner | None = None):
        self.registry = registry
        self.detector = TemplateDetector(registry)
        self.runner = runner or PandocRunner()
        self.filters_dir = Path(__file__).resolve().parents[1] / "assets" / "filters"

    def build_plan(self, ctx: PipelineContext) -> PipelinePlan:
        template = self.detector.guess(ctx.source_path, ctx.template_name)
        preprocessor_entries = template.preprocessors()
        filter_entries = template.filters()
        preprocessors = [entry["name"] for entry in preprocessor_entries]
        filters = [entry["name"] for entry in filter_entries]
        postprocessors = list(template.data.get("postprocessors", []))
        post_args = postprocessor_registry.collect_args(postprocessors)
        filter_args: list[str] = []
        metadata_args: list[str] = []
        for entry in filter_entries:
            name = entry["name"]
            if entry.get("lua"):
                lua_path = entry.get("path")
                if not lua_path:
                    lua_name = name if name.endswith(".lua") else f"{name}.lua"
                    lua_path = self.filters_dir / lua_name
                filter_args.append(f"--lua-filter={lua_path}")
            else:
                filter_args.extend(["--filter", name])
            metadata = entry.get("metadata")
            if metadata:
                if isinstance(metadata, str):
                    metadata_args.extend(["--metadata-file", metadata])
                elif isinstance(metadata, list):
                    for metadata_path in metadata:
                        metadata_args.extend(["--metadata-file", metadata_path])
                else:
                    raise TemplateConfigError(
                        f"Filter '{entry['name']}' metadata must be string or list."
                    )
        for metadata_path in ctx.metadata_files:
            metadata_args.extend(["--metadata-file", str(metadata_path)])
        for lua_path in ctx.lua_filters:
            filter_args.append(f"--lua-filter={lua_path}")
        for binary_name in ctx.exec_filters:
            filter_args.extend(["--filter", binary_name])
        citations = template.citations()
        citation_args: list[str] = []
        if ctx.citeproc:
            citation_args.append("--citeproc")
        metadata_entries = citations.get("metadata")
        if metadata_entries:
            entries = [metadata_entries] if isinstance(metadata_entries, str) else list(metadata_entries)
            for metadata_entry in entries:
                citation_args.extend(["--metadata-file", str(metadata_entry)])
        csl = citations.get("csl")
        if csl:
            citation_args.extend(["--csl", str(csl)])
        if ctx.csl is not None:
            citation_args.extend(["--csl", str(ctx.csl)])
        bibliography = citations.get("bibliography")
        if bibliography:
            bib_entries = [bibliography] if isinstance(bibliography, str) else list(bibliography)
            for bib_entry in bib_entries:
                citation_args.extend(["--bibliography", str(bib_entry)])
        for bibliography_path in ctx.bibliography_paths:
            citation_args.extend(["--bibliography", str(bibliography_path)])
        ctx.workdir.mkdir(parents=True, exist_ok=True)
        intermediate_tex = ctx.workdir / f"{ctx.source_path.stem}.preprocessed.tex"
        ctx.output_path.parent.mkdir(parents=True, exist_ok=True)
        spec = template.pandoc_spec()
        if ctx.reference_doc is not None:
            spec["reference_doc"] = str(ctx.reference_doc)
        if ctx.top_level_division:
            raw_args = spec.get("args", [])
            args = list(raw_args) if isinstance(raw_args, list) else []
            args.extend(["--top-level-division", ctx.top_level_division])
            spec["args"] = args
        pandoc_command = self.runner.build_command(
            source_tex=intermediate_tex,
            output_docx=ctx.output_path,
            spec=spec,
            extra_args=citation_args + metadata_args + filter_args + post_args,
        )
        return PipelinePlan(
            template=template,
            preprocessors=preprocessors,
            filters=filters,
            postprocessors=postprocessors,
            pandoc_command=pandoc_command,
            intermediate_tex=intermediate_tex,
            resolved_reference_doc=ctx.reference_doc,
            resolved_metadata_files=list(ctx.metadata_files),
            resolved_lua_filters=list(ctx.lua_filters),
            resolved_exec_filters=list(ctx.exec_filters),
            resolved_csl=ctx.csl,
            resolved_bibliography=list(ctx.bibliography_paths),
            resolved_top_level_division=ctx.top_level_division,
            citeproc_enabled=ctx.citeproc,
        )

    def run(self, ctx: PipelineContext) -> PipelinePlan:
        plan = self.build_plan(ctx)
        text = ctx.source_path.read_text(encoding="utf-8")
        metadata = {
            "source_path": ctx.source_path,
            "source_dir": ctx.source_path.parent,
            "workspace_root": (ctx.workspace_root or ctx.source_path.parent),
            "generated_images_dir": ctx.workdir / "generated-images",
            "image_conversions": [],
            "image_conversion_failures": [],
            "fallbacks": [],
            "generated_image_files": [],
            "image_conversion_cache": {},
        }
        processed_text, executed, preprocessor_metadata = run_preprocessors(
            plan.preprocessors,
            text,
            metadata,
        )
        plan.executed_preprocessors = executed
        plan.intermediate_tex.write_text(processed_text, encoding="utf-8")
        image_conversions = preprocessor_metadata.get("image_conversions", [])
        image_conversion_failures = preprocessor_metadata.get("image_conversion_failures", [])
        fallbacks = preprocessor_metadata.get("fallbacks", [])
        generated_image_files = preprocessor_metadata.get("generated_image_files", [])
        if isinstance(image_conversions, list):
            plan.image_conversions = image_conversions
        if isinstance(image_conversion_failures, list):
            plan.image_conversion_failures = image_conversion_failures
        if isinstance(fallbacks, list):
            plan.fallbacks = fallbacks
        if isinstance(generated_image_files, list):
            plan.generated_image_files = [path for path in generated_image_files if isinstance(path, Path)]
        self.runner.run(plan.pandoc_command, dry_run=ctx.dry_run)
        return plan
