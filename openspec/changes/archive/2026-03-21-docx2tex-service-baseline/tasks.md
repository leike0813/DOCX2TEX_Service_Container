## 1. Baseline Framing

- [x] 1.1 Create the `docx2tex-service-baseline` change scaffold under the default `spec-driven` workflow.
- [x] 1.2 Draft the proposal so it defines the baseline as a code-backed service contract rather than a target-state roadmap.

## 2. Capability Specs

- [x] 2.1 Write the `conversion-api` spec for the currently implemented HTTP endpoints and supported request inputs.
- [x] 2.2 Write the `job-execution-and-packaging` spec for task execution, state transitions, and debug/non-debug packaging behavior.
- [x] 2.3 Write the `cache-and-postprocess` spec for cache coordination, cache key composition, and TeX/image post-processing behavior.

## 3. Architecture Capture

- [x] 3.1 Draft the design document to record the current service-layer architecture and runtime dependencies.
- [x] 3.2 Document the baseline boundaries for unsupported or partially implemented surfaces, including `/v1/nocache` and `FontMapsZip`.

## 4. Validation

- [x] 4.1 Cross-check each requirement against the current code paths in routes, job orchestration, cache, and post-processing modules.
- [x] 4.2 Run OpenSpec status and validation commands and fix any artifact structure or wording issues they report.
