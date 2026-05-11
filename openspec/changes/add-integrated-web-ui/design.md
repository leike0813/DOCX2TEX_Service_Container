## Context

The current repository packages a FastAPI service around the upstream `docx2tex` pipeline. It already supports multipart job submission and asynchronous result retrieval, but it has no built-in browser UI. The container starts a single `uvicorn` process, so the new UI needs to be served by the same application rather than by a separate frontend runtime.

The service also has an important API constraint: built-in repository config files can only be used today by uploading them as files. That is workable for CLI clients but not for a WebUI that needs to expose a curated set of server-side presets. This change therefore needs a small API extension alongside the page itself.

## Goals / Non-Goals

**Goals:**
- Serve a simple browser UI directly from the existing FastAPI app.
- Let users drag and drop a single DOCX, choose built-in presets, toggle `debug`, submit a job, observe status, and download the ZIP result.
- Keep preset definitions controlled by the backend so the UI stays aligned with repository-supported options.
- Extend the existing `POST /v1/task` path rather than creating a separate task submission pipeline for the UI.

**Non-Goals:**
- Add a separate SPA toolchain, Node-based build, or second container process.
- Support URL-based submission, free-form config upload, `FontMapsZip`, `custom_evolve`, Dry-run UI, or user-authenticated history in the first release.
- Change task state persistence, packaging rules, or cache semantics beyond what is already covered by the current service.

## Decisions

### Decision: Serve the UI from the current FastAPI process

The UI will be delivered by the existing service at `GET /`, using static HTML/CSS/JavaScript assets and normal FastAPI routing.

**Rationale:** This matches the deployment constraint that the container should start one integrated service and avoids introducing a separate frontend runtime or reverse-proxy setup.

**Alternatives considered:**
- A separate frontend app with its own build chain. Rejected because it adds operational and packaging complexity that the first release does not need.
- Embedding the existing Appsmith export. Rejected because the repository only contains an exported prototype, not an integrated runtime, and the project constraint is an in-container built-in UI.

### Decision: Backend-owned preset metadata and preset resolution

The backend will expose a preset metadata endpoint and will resolve preset identifiers to repository-controlled file paths during task submission.

**Rationale:** The browser cannot safely or meaningfully submit repository-local config files on its own. A backend-owned mapping keeps the source of truth in one place and prevents the UI from drifting.

**Alternatives considered:**
- Hard-code preset lists in frontend JavaScript. Rejected because it creates duplicate configuration knowledge and makes later preset changes easy to miss.
- Dynamically scan directories at runtime. Rejected because the first release only needs a curated whitelist and should avoid turning test/example files into public options by accident.

### Decision: Extend `POST /v1/task` instead of adding a UI-only submission API

The existing task creation endpoint will accept `conf_preset` and `custom_xsl_preset` as optional multipart fields, with explicit mutual exclusion against uploaded `conf` and `custom_xsl` files.

**Rationale:** This preserves a single task submission path, keeps the UI thin, and makes the preset mechanism reusable by future clients.

**Alternatives considered:**
- Add a separate UI-only task creation endpoint. Rejected because it would duplicate validation and request-preparation logic already present in the service.
- Keep the backend unchanged and have the UI emulate uploads. Rejected because browser code cannot turn server-side repository files into uploads without an additional backend resolution step.

### Decision: Limit first-release controls to repository-supported, service-owned presets

The first UI release will expose only the four repository `conf/*.xml` presets, one repository-owned `custom_xsl` preset (`force-zh-cn-lang`), `debug`, `TableModel`, and `MathTypeSource`.

**Rationale:** These are the options that can be clearly sourced from the repository and productized without exposing test fixtures or upstream sample files as supported options.

**Alternatives considered:**
- Also expose `custom_evolve` presets from test files or upstream examples. Rejected because those files are not project-owned supported presets.
- Expose every current API field in the UI. Rejected because the first release is intentionally narrow and should optimize for a clean conversion flow.

## Risks / Trade-offs

- **[Risk]** Serving a static UI from the API app can blur concerns between frontend and backend code. → **Mitigation:** Keep the UI asset footprint small and isolated to a dedicated static/template location.
- **[Risk]** Preset mappings can drift from actual repository files if renamed. → **Mitigation:** Centralize preset definitions in backend code and cover them with route tests.
- **[Risk]** The current `/v1/task` contract becomes slightly more complex due to preset/file mutual exclusion. → **Mitigation:** Validate conflicts early and keep the new fields optional and additive.
- **[Risk]** Users may assume the WebUI supports all documented API features. → **Mitigation:** Make first-release boundaries explicit in the UI copy and in the new spec requirements.

## Migration Plan

No data migration is required.

Implementation rollout:
1. Add the OpenSpec change artifacts.
2. Implement backend preset metadata and preset-aware task submission.
3. Add the integrated UI page and static assets.
4. Add tests for page rendering, preset metadata, task submission validation, and UI success/error behavior.

Rollback strategy:
- Revert the UI routes and static assets while leaving the existing API routes intact.
- Remove preset-aware request handling if it causes regressions in task submission.

## Open Questions

None. The first release scope, UI delivery model, preset ownership, and API extension approach are fixed by this change.
