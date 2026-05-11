# Proposal: rebuild-platform-around-capability-matrix

## Why

The repository currently exposes a refactored service shell, but its internal model is
still direction-centric and tied too closely to the current `docx2tex` implementation.
That makes future growth awkward:

- `docx -> latex` is treated as if it were identical to the `docx2tex` engine
- `latex -> docx` is still only a placeholder instead of a real matrix cell
- the external `tex2docx_pandoc` codebase cannot be absorbed cleanly without another
  architectural reset

This change rebuilds the platform around a capability matrix where `conversion path ×
engine` is the first-class concept.

## What Changes

- add a new platform package `src/document_conversion/`
- split engine implementations into `src/engines/docx2tex_engine/` and
  `src/engines/pandoc_engine/`
- make profiles path-scoped and engine-backed
- expose a matrix-aware capability registry and profile registry
- absorb the formal `tex2docx_pandoc/pipeline/` code into `pandoc_engine`
- implement `latex -> docx@pandoc` and `docx -> latex@pandoc`
- keep `src/docx2tex_service/` as a compatibility shell only

## Impact

- `document_conversion` becomes the formal platform source of truth
- API payloads for capabilities and profiles become matrix-shaped
- `/v2/tasks` resolves `profile_id -> path -> engine`, instead of resolving by direction
- future additions such as `latex -> markdown@pandoc` can be introduced without another
  platform rewrite
