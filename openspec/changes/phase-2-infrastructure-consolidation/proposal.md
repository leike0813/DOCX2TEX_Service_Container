## Why

The first platform refactor established the new `src/docx2tex_service/` package, but the service still depended on legacy infrastructure modules under `app/`, still carried legacy HTTP routes, and still kept duplicated tests and historical clutter in the repository root.

This change finishes the consolidation. It makes `src/docx2tex_service/` the only formal implementation tree, removes the old task compatibility surface, cleans repository leftovers, and leaves the project in a shape that can support future converters and UI evolution without another large structural rewrite.

## What Changes

- Move the remaining infrastructure responsibilities from `app/` into `src/docx2tex_service/infrastructure/`
- Remove legacy task endpoints and keep the platform surface as the only supported API
- Move WebUI resources under `src/docx2tex_service/interfaces/webui/`
- Remove flat legacy tests and keep only layered tests under `tests/unit`, `tests/integration`, `tests/api`, and `tests/e2e`
- Update Docker, local deployment docs, API docs, and quality tool configuration to the final `src/`-only structure
- Remove obsolete directories, generated artifacts, and legacy documentation files from the main repository layout

## Impact

- Existing `/v1/task*`, `/v1/ui/presets`, and `/v1/dryrun` clients must migrate to `/v2/tasks*`, `/v1/profiles`, and `/v2/dryrun`
- `src/docx2tex_service/` becomes the sole implementation root for future feature work
- Testing, typing, linting, and deployment no longer need to account for transitional `app/` code paths
