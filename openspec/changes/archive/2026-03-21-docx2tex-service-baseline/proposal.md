## Why

The repository has a working `docx2tex` service wrapper, but it does not yet have an OpenSpec baseline that captures what the service actually does today. A baseline change is needed now so later fixes and extensions can describe deltas against a stable, code-backed contract instead of drifting documentation.

## What Changes

- Create the first OpenSpec baseline change for the current FastAPI service implementation.
- Define the service's public HTTP behavior for task creation, task status, result download, dry-run generation, health checks, and version reporting.
- Define the current background execution, packaging, cache, and post-processing behavior that can be verified directly from the codebase.
- Exclude behaviors that are not fully implemented from the supported baseline, including `/v1/nocache` and `FontMapsZip` as a conversion feature.

## Capabilities

### New Capabilities
- `conversion-api`: Baseline requirements for the currently implemented HTTP endpoints and request handling.
- `job-execution-and-packaging`: Baseline requirements for task state transitions, background execution, and ZIP packaging behavior.
- `cache-and-postprocess`: Baseline requirements for cache coordination, cache key composition, and TeX post-processing behavior.

### Modified Capabilities

None.

## Impact

- Affects OpenSpec artifacts under `openspec/changes/docx2tex-service-baseline/`.
- Documents behavior implemented in the FastAPI routes, `JobManager`, cache/lock storage, post-processing helpers, and container-provided runtime dependencies.
- Establishes the baseline for future service changes without modifying runtime code or the bundled upstream `docx2tex` sources.
