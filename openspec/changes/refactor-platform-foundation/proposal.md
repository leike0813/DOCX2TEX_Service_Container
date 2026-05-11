## Why

The service had grown around a single conversion path and a route-centric implementation. That made new features expensive to add, blurred the boundary between HTTP concerns and conversion orchestration, and left local deployment and testing under-specified.

This change establishes a platform foundation for long-term evolution. It keeps the current `docx -> latex` path working, but reorganizes the service around a converter registry, platform request model, layered architecture, local deployment guidance, and a structured test layout.

## What Changes

- Add a new platform package under `src/docx2tex_service/`
- Introduce platform domain models, application services, converter registry, and runtime assembly
- Keep `docx2tex` as the implemented converter and add planned `pandoc` capability placeholders
- Add platform endpoints for capabilities, profiles, and `/v2/tasks`
- Keep `/v1/task` and related routes as compatibility endpoints
- Repoint the integrated WebUI to platform-native endpoints while retaining compatibility presets
- Upgrade project metadata to `pyproject.toml`
- Add local deployment and test architecture documentation
- Add layered tests under `tests/unit`, `tests/integration`, `tests/api`, and `tests/e2e`

## Impact

- Existing clients can keep using `/v1/task`
- New UI and future converters can target `/v2/tasks` and shared profile/capability endpoints
- Local development no longer depends on container-only default paths
- Future `latex -> docx` and `latex -> markdown` work can be added as converters instead of route-specific forks
