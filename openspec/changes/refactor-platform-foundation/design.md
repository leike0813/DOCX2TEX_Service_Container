# Design

## Scope

This refactor is a platform foundation change. It does not implement `latex -> docx` or `latex -> markdown`, but it restructures the code so those directions can be added without another route-layer rewrite.

## Layered Architecture

### Domain

`src/docx2tex_service/domain/` defines:

- `DocumentFormat`
- `ConversionDirection`
- `InputSource`
- `ConversionRequest`
- `ConversionJob`
- `ConversionProfile`
- `Converter`
- `ConverterRegistry`

These types are platform-level and no longer tied to `docx2tex` naming.

### Application

`src/docx2tex_service/application/platform.py` defines `PlatformService`, which owns:

- capability listing
- profile listing
- platform task submission
- compatibility task submission
- task lookup
- result lookup

The service maps HTTP requests into platform submissions and delegates execution to a converter chosen by direction.

### Infrastructure

`src/docx2tex_service/infrastructure/` assembles the concrete runtime:

- `Docx2TexConverter`
- `PlannedConverter`
- profile registry payloads
- runtime wiring for config, SQLite, cache, tasks, and `JobManager`

The existing `app.core.*` and `app.services.job_manager` modules remain in place as reused infrastructure during this phase.

### Interfaces

- `src/docx2tex_service/interfaces/api/`
- `src/docx2tex_service/interfaces/cli.py`
- `app/webui/`

The API layer now owns HTTP surface only. Task submission logic is pushed into the platform service and converter adapter.

## Compatibility Strategy

### Kept

- `/v1/task`
- `/v1/task/{task_id}`
- `/v1/task/{task_id}/result`
- `/v1/ui/presets`
- `/healthz`
- `/version`
- `/v1/dryrun`

### Added

- `/v1/capabilities`
- `/v1/profiles`
- `/v2/tasks`
- `/v2/tasks/{task_id}`
- `/v2/tasks/{task_id}/result`

### Removed

- `/v1/nocache` now returns `410 Gone`

## Runtime Defaults

Non-container defaults now point to repository-local `.local/` paths. Containers still override them through environment variables.

## Test Strategy

The test tree is split into:

- `tests/unit`
- `tests/integration`
- `tests/api`
- `tests/e2e`

Legacy flat tests remain as compatibility regression coverage during the transition.
