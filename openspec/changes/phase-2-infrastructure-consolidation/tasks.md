## 1. Infrastructure Consolidation

- [x] 1.1 Move the remaining runtime infrastructure from `app/` into `src/docx2tex_service/infrastructure/`.
- [x] 1.2 Replace the old `JobManager` shape with dedicated task state, execution, packaging, and maintenance components.
- [x] 1.3 Serve WebUI assets from `src/docx2tex_service/interfaces/webui/` only.

## 2. API Consolidation

- [x] 2.1 Remove `/v1/task*`, `/v1/ui/presets`, and `/v1/dryrun`.
- [x] 2.2 Keep only the platform task surface plus `healthz`, `version`, and `GET /`.

## 3. Repository Hygiene

- [x] 3.1 Remove the legacy `app/` Python implementation and `app/requirements.txt`.
- [x] 3.2 Remove flat legacy tests and keep only the layered test tree.
- [x] 3.3 Clean obsolete docs, runtime output directories, and abandoned repository clutter.

## 4. Validation

- [x] 4.1 Update deployment, architecture, API, and testing documentation to the final structure.
- [x] 4.2 Run pytest, mypy, ruff, and strict OpenSpec validation.
