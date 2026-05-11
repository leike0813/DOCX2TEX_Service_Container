## 1. Platform Foundation

- [x] 1.1 Create the new `src/docx2tex_service/` package and split platform concerns into domain, application, infrastructure, and interfaces layers.
- [x] 1.2 Introduce a converter registry, shared conversion models, and a planned-converter placeholder for future `pandoc` directions.

## 2. API And UI Migration

- [x] 2.1 Add platform capability and profile endpoints and introduce `/v2/tasks` as the platform-native task entrypoint.
- [x] 2.2 Keep `/v1/task` and related endpoints as compatibility routes while moving orchestration into the platform service.
- [x] 2.3 Update the integrated WebUI to consume platform-native profile and task endpoints.

## 3. Engineering Foundation

- [x] 3.1 Add `pyproject.toml` and standardize lint, type-check, and packaging metadata around it.
- [x] 3.2 Add non-container local deployment documentation and make default runtime paths repository-local instead of container-only.
- [x] 3.3 Update container startup to serve the refactored platform app and WebUI together.

## 4. Test Architecture

- [x] 4.1 Add layered tests under `tests/unit`, `tests/integration`, `tests/api`, and `tests/e2e`.
- [x] 4.2 Keep legacy route tests passing as compatibility regression coverage.

## 5. Validation

- [x] 5.1 Run pytest across legacy and new layered tests.
- [x] 5.2 Run mypy for `app` and `src`.
- [x] 5.3 Run ruff checks.
- [x] 5.4 Validate the OpenSpec change in strict mode.
