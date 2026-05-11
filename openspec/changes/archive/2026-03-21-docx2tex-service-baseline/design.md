## Context

The current project is a service wrapper around the upstream `docx2tex` pipeline. The service is implemented as a FastAPI application that persists task and cache state in SQLite, runs conversion jobs in a thread pool, invokes Calabash against the bundled upstream `docx2tex.xpl`, and post-processes generated TeX artifacts before publishing ZIP files from a public work directory.

This change is documentation-only. Its purpose is to capture the current service behavior as a verifiable baseline. The baseline must match the code as it exists today, not the README's broader claims and not potential future fixes.

## Goals / Non-Goals

**Goals:**
- Define a baseline for the service layer only.
- Split the baseline into a small set of capability specs that map cleanly to the current code structure.
- Record only behaviors that can be confirmed directly from the implementation.
- Make future service changes expressible as deltas against this baseline.

**Non-Goals:**
- Specify the internal behavior of the upstream `docx2tex` project in detail.
- Correct implementation defects or align runtime behavior with the README as part of this change.
- Treat `/v1/nocache` or `FontMapsZip` conversion support as stable, supported capabilities.

## Decisions

### Decision: Model the baseline at the service boundary

The change defines capabilities around HTTP behavior, job orchestration, and cache/post-processing rather than around upstream `docx2tex` internals.

**Rationale:** The repository's maintained surface is the service wrapper. The upstream pipeline is bundled, but this change is meant to baseline the service implementation that this repository owns.

**Alternatives considered:**
- Model the upstream `docx2tex` pipeline as first-class capabilities. Rejected because it would expand scope beyond the service layer and duplicate upstream concerns.
- Use a single broad capability for the whole service. Rejected because it would make later deltas harder to express and review.

### Decision: Use three capabilities that mirror the current implementation seams

The baseline is split into `conversion-api`, `job-execution-and-packaging`, and `cache-and-postprocess`.

**Rationale:** These three areas map directly to the code organization: routes own request handling, `JobManager` owns job progression and packaging, and the cache/post-process modules own reuse and output rewriting.

**Alternatives considered:**
- One capability per endpoint. Rejected because packaging, cache, and task orchestration are cross-endpoint behaviors.
- A separate capability for StyleMap only. Rejected because StyleMap is currently one part of the post-processing and request preparation path rather than a standalone product surface.

### Decision: Baseline only code-proven behavior

The specs describe only behaviors that are already implemented and traceable in code. Claims that exist only in README or API docs are excluded unless the code supports them end to end.

**Rationale:** The baseline is meant to be a trustworthy reference. If it includes aspirational or broken behavior, future changes will be comparing against the wrong contract.

**Alternatives considered:**
- Baseline the documented API surface as-is. Rejected because it would incorrectly treat `/v1/nocache` and `FontMapsZip` conversion support as working features.
- Add future-looking requirements with caveats. Rejected because this change is intended to freeze current reality, not roadmap intent.

### Decision: Treat unsupported or broken surfaces as explicit exclusions

`/v1/nocache` is not included as a supported endpoint in the baseline because the route uses an undefined `image_dir` variable. `FontMapsZip` is recorded only where it affects persisted input and cache key calculation, not as a supported conversion customization path.

**Rationale:** These behaviors are observable in the code and materially affect what the service can be relied on to do today.

**Alternatives considered:**
- Ignore these gaps entirely. Rejected because it would blur the boundary between supported and unsupported behavior.
- Add them as requirements and note they are currently failing. Rejected because that would turn the baseline into a target-state spec instead of a current-state spec.

## Risks / Trade-offs

- **[Risk]** The baseline may become stale as the service evolves. → **Mitigation:** Future code changes should update the relevant capability deltas in OpenSpec as part of the change.
- **[Risk]** Excluding partially wired features may surprise readers who compare the specs to README claims. → **Mitigation:** The proposal and design explicitly state that the baseline follows implementation, not documentation claims.
- **[Risk]** Service-only scoping leaves upstream pipeline details underspecified. → **Mitigation:** The design records the upstream integration boundary and leaves deeper `docx2tex` behavior to later, separate work if needed.

## Migration Plan

No runtime migration is required. This change adds OpenSpec artifacts only.

Rollout steps:
1. Create the baseline change artifacts.
2. Verify that each requirement maps to an implemented code path.
3. Run OpenSpec status and validation commands.

Rollback strategy:
- Remove the change directory if the baseline artifacts are found to be inaccurate before adoption.

## Open Questions

None for this baseline change. Known gaps such as `/v1/nocache` and `FontMapsZip` are intentionally excluded from supported baseline behavior rather than left unresolved.
