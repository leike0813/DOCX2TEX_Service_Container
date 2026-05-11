# Design

## Scope

This change finalizes the platform consolidation started by `refactor-platform-foundation`. It does not add new conversion directions, but it removes the transitional split between a new `src/` platform layer and legacy `app/` infrastructure.

## Infrastructure Consolidation

All concrete runtime responsibilities now live under `src/docx2tex_service/infrastructure/`:

- configuration and runtime paths
- SQLite persistence
- cache metadata and build locks
- task state persistence
- `docx2tex` execution
- packaging and post-processing
- StyleMap preprocessing
- maintenance cleanup

The former `JobManager` responsibilities are split across:

- `state.py`
- `executor.py`
- `runner.py`
- `packaging.py`
- `maintenance.py`

`PlatformContext` now wires only `src/` components.

## API Surface

The supported API surface after consolidation is:

- `GET /`
- `GET /healthz`
- `GET /version`
- `GET /v1/capabilities`
- `GET /v1/profiles`
- `POST /v2/tasks`
- `GET /v2/tasks/{task_id}`
- `GET /v2/tasks/{task_id}/result`
- `POST /v2/dryrun`

Removed legacy endpoints:

- `POST /v1/task`
- `GET /v1/task/{task_id}`
- `GET /v1/task/{task_id}/result`
- `GET /v1/ui/presets`
- `POST /v1/dryrun`

## Repository Hygiene

The repository keeps only production or still-useful assets in top-level directories. Generated runtime outputs, editor caches, and abandoned prototypes are removed from the main layout. Historical experiments are no longer part of the active project surface and are recoverable from Git history if needed.

## Testing Strategy

The test suite is fully layered:

- `tests/unit`
- `tests/integration`
- `tests/api`
- `tests/e2e`

Flat `tests/test_*.py` files are removed. API tests verify that removed legacy endpoints now return `404`.
