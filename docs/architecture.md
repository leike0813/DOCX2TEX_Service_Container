# docx2tex_inverse Architecture

This document summarizes the service architecture, key components, and data flow.

## Overview

- Tech stack: FastAPI (HTTP), SQLite (state/cache metadata), XProc/Calabash (docx2tex pipeline), XSLT 2.0 (evolve/xml2tex), Inkscape (vector → PDF).
- Goal: Convert DOCX to LaTeX (TeX) with a configurable, extensible, offline‑friendly service.
- Highlights:
  - Pluggable configuration: xml2tex conf (`conf/`), custom evolve‑driver, optional custom XSL between evolve→xml2tex.
  - StyleMap: map Word visible styles to canonical roles (Title/Heading1..3) and inject the corresponding LaTeX according to conf.
  - Cache + locks: input‑based cache_key; concurrent builders are coordinated; cache is self‑healing.
  - Post‑processing: vector conversion, image packaging, VSDX handling, width normalization.

## Directory Layout

- `app/core/`
  - `config.py` (env/paths), `db.py`, `models.py`
  - `cache.py` (CacheStore) + `LockManager`
  - `storage.py`, `logging.py`, `convert.py`, `proc.py`, `tasks.py`, `cleanup.py`
  - `postprocess.py` (unified: collect+rewrite images, drop/comment VSDX, normalize widths, convert vector refs)
  - `stylemap.py` (prepare_effective_xsls; StyleMap uses evolve‑driver injection only)
- `app/services/`
  - `job_manager.py` (orchestration: create/state, cache hit/build, post‑process, packaging, manifest)
  - `context.py` (optional)
- `app/api/`
  - `routes.py` (`/v1/task`, `/v1/dryrun`, `/v1/task/{id}`, `/v1/task/{id}/result`, `/healthz`, `/version`)
- `app/server.py` (mount router, start cleanup + lock sweeper)
- Others: `conf/`, `catalog/`, `docs/`, `tests/`, `Dockerfile`

Note: legacy utilities under `app/scripts/` were refactored into `core/postprocess.py` and `core/stylemap.py` and are no longer used.

## Data Flow

1) `POST /v1/task`
   - Accept `file` or `url`; optional `conf/custom_evolve/StyleMap/FontMapsZip/MathTypeSource/TableModel`.
   - Persist JobState (pending), save inputs.
   - If `StyleMap` is given, build an effective evolve‑driver XSL (`custom-evolve-effective.xsl`) and write `stylemap_manifest.json`.
   - Compute `cache_key`; return `task_id` + `cache_status`.

2) Background processing (JobManager)
   - Cache HIT → restore previous products; else run Calabash (docx2tex.xpl) to produce `.tex/.xml` and publish to cache.
   - Optional vector conversion: `.emf/.wmf/.svg` → `.pdf` with Inkscape; update references in TeX.
   - Non‑debug (debug=false): collect referenced images to `image/`, rewrite paths, drop `.vsdx`, normalize widths.
   - Debug (debug=true): comment `.vsdx` includes and normalize widths.
   - Package ZIP:
     - Non‑debug: `<base>.tex` + `image/`.
     - Debug: `.tex/.xml`, `<base>.debug/`, `<base>.docx.tmp/`, `logs/<task_id>.log`, `xsl/custom-evolve-effective.xsl` (if exists), `stylemap_manifest.json` (if exists).

3) Query & download
   - `GET /v1/task/{task_id}` → state; `GET /v1/task/{task_id}/result` → ZIP when done.

4) Cleanup & locks
   - `cleanup.py` removes expired tasks/caches (TTL‑driven) with two‑phase deletion; `LockManager` sweeps stale locks.

## Cache Key

`cache_key = SHA256(DOCX + conf + custom_xsl + custom_evolve + MathTypeSource + TableModel + FontMapsZip)`

Independent of `debug` and `img_post_proc` so debug/non‑debug share cache.

## StyleMap Injection Policy

- StyleMap uses evolve‑driver injection only (no separate output‑layer custom XSL). The router passes `custom-evolve-effective.xsl` to the pipeline when present.

## Tests

- Unit: config/storage/cache/tasks/convert/proc
- Post‑process: `tests/test_postprocess.py`
- StyleMap: `tests/test_stylemap_effective.py`
- Routes: `tests/test_routes_basic.py`, `tests/test_routes_dryrun.py`, `tests/test_routes_task.py` (require `httpx`)

