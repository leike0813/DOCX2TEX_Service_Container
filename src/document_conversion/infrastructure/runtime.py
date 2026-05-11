from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from engines.docx2tex_engine.executor import TaskExecutor
from engines.docx2tex_engine.converter import Docx2TexEngine
from engines.docx2tex_engine.presets import (
    CUSTOM_XSL_PRESETS,
    DEFAULTS,
    MATH_TYPE_SOURCES,
    TABLE_MODELS,
)
from engines.docx2tex_engine.profiles import DOCX2TEX_PROFILES
from document_conversion.domain import EngineRegistry
from engines.pandoc_engine.converter import PANDOC_PROFILES, PandocEngine
from engines.pandoc_engine.resources import latex_to_docx_option_payload

from .cache import CacheStore, LockManager
from .config import Config
from .database import Database
from .maintenance import start_cleanup_loop
from .state import TaskStore


@dataclass
class PlatformContext:
    cfg: Config
    db: Database
    cache: CacheStore
    locks: LockManager
    tasks: TaskStore
    jobs: TaskExecutor
    registry: EngineRegistry

    def capabilities_payload(self) -> dict[str, Any]:
        cells = [
            {
                "path_id": cell.path_id,
                "engine_id": cell.engine_id,
                "source_format": cell.source_format.value,
                "target_format": cell.target_format.value,
                "status": cell.status,
                "description": cell.description,
            }
            for cell in self.registry.all_cells()
        ]
        path_rows = sorted(
            {
                (
                    cell["path_id"],
                    cell["source_format"],
                    cell["target_format"],
                )
                for cell in cells
            }
        )
        return {
            "capabilities": cells,
            "matrix": {
                "cells": cells,
                "paths": [
                    {
                        "path_id": path_id,
                        "source_format": source_format,
                        "target_format": target_format,
                    }
                    for path_id, source_format, target_format in path_rows
                ],
            },
        }

    def profiles_payload(self) -> dict[str, Any]:
        grouped = self.registry.profiles_by_path()
        grouped_payload = {
            path_id: [
                {
                    "id": profile.id,
                    "label": profile.label,
                    "path_id": profile.path_id,
                    "engine_id": profile.engine_id,
                    "description": profile.description,
                }
                for profile in profiles
            ]
            for path_id, profiles in grouped.items()
        }
        docx_ui_profiles = grouped_payload.get("docx_to_latex", [])
        docx_ui_profiles = [
            profile for profile in docx_ui_profiles if profile["engine_id"] == "docx2tex"
        ]
        pandoc_defaults = latex_to_docx_option_payload()
        return {
            "profiles": docx_ui_profiles,
            "profiles_by_path": grouped_payload,
            "matrix_profiles": [
                profile for profiles in grouped_payload.values() for profile in profiles
            ],
            "option_presets": {
                "custom_xsl": [
                    {"id": preset_id, "label": str(meta["label"])}
                    for preset_id, meta in CUSTOM_XSL_PRESETS.items()
                ],
                "table_model": TABLE_MODELS,
                "math_type_source": MATH_TYPE_SOURCES,
            },
            "path_options": {
                "docx_to_latex": {
                    "custom_xsl": [
                        {"id": preset_id, "label": str(meta["label"])}
                        for preset_id, meta in CUSTOM_XSL_PRESETS.items()
                    ],
                    "table_model": TABLE_MODELS,
                    "math_type_source": MATH_TYPE_SOURCES,
                },
                "latex_to_docx": pandoc_defaults,
            },
            "defaults": {
                "profile_id": "docx_to_latex/docx2tex-ctexbook",
                "custom_xsl_preset": DEFAULTS["custom_xsl_preset"],
                "table_model": DEFAULTS["table_model"],
                "math_type_source": DEFAULTS["math_type_source"],
                "debug": DEFAULTS["debug"],
                "source_format": "docx",
                "target_format": "latex",
                "by_path": {
                    "docx_to_latex": {
                        "profile_id": "docx_to_latex/docx2tex-ctexbook",
                        "custom_xsl_preset": DEFAULTS["custom_xsl_preset"],
                        "table_model": DEFAULTS["table_model"],
                        "math_type_source": DEFAULTS["math_type_source"],
                        "debug": DEFAULTS["debug"],
                    },
                    "latex_to_docx": {
                        "profile_id": "latex_to_docx/pandoc-auto",
                        "debug": False,
                    },
                },
            },
            "profile_catalog": {
                "docx2tex": [profile.id for profile in DOCX2TEX_PROFILES],
                "pandoc": [profile.id for profile in PANDOC_PROFILES],
            },
        }


def build_platform_context() -> PlatformContext:
    cfg = Config.from_env()
    db = Database(cfg.db_path)
    db.init_schema()
    cache = CacheStore(db, cfg.data_root)
    locks = LockManager(db)
    tasks = TaskStore(db)
    jobs = TaskExecutor(cfg, tasks, cache, locks, workers=cfg.uvicorn_workers)
    registry = EngineRegistry()
    registry.register(Docx2TexEngine())
    registry.register(PandocEngine())
    return PlatformContext(
        cfg=cfg,
        db=db,
        cache=cache,
        locks=locks,
        tasks=tasks,
        jobs=jobs,
        registry=registry,
    )


def start_platform_runtime(ctx: PlatformContext) -> None:
    ctx.cfg.data_root.mkdir(parents=True, exist_ok=True)
    ctx.cfg.public_root.mkdir(parents=True, exist_ok=True)
    ctx.cfg.log_dir.mkdir(parents=True, exist_ok=True)
    retention: Optional[int] = ctx.cfg.ttl_days
    start_cleanup_loop(ctx.cfg, ctx.db, ctx.cache, retention, retention)
    ctx.locks.start_sweeper(ctx.cfg.lock_sweep_interval_sec, ctx.cfg.lock_max_age_sec)


_CONTEXT: PlatformContext | None = None


def get_platform_context() -> PlatformContext:
    global _CONTEXT
    if _CONTEXT is None:
        _CONTEXT = build_platform_context()
    return _CONTEXT
