# Design: rebuild-platform-around-capability-matrix

## Architecture

The new architecture separates platform concerns from engine concerns.

### Platform package

`src/document_conversion/` owns:

- path and format models
- capability matrix and profile registry
- unified task submission service
- API and CLI entrypoints
- runtime assembly

The platform task graph is:

1. `prepare`
2. `resolve_profile`
3. `resolve_engine`
4. `execute`
5. `package`
6. `publish`

### Engine packages

`src/engines/docx2tex_engine/` owns:

- `docx -> latex@docx2tex`
- docx2tex-facing profiles and option presets
- docx2tex-specific submission preparation

`src/engines/pandoc_engine/` owns:

- `docx -> latex@pandoc`
- `latex -> docx@pandoc`
- planned `latex -> markdown@pandoc`
- absorbed template registry, detector, preprocessors, filters, and Pandoc runner

## Profile resolution

Profiles are public user-facing selections. Each profile belongs to exactly one conversion
path and maps to exactly one engine.

Examples:

- `docx_to_latex/docx2tex-ctexbook`
- `docx_to_latex/pandoc-default`
- `latex_to_docx/pandoc-ctexbook`

The platform never exposes a public `engine_id` input field for task submission.

## Compatibility

`src/docx2tex_service/` remains in the tree as a migration layer only. Public runtime
entrypoints are forwarded to `document_conversion`.

The current WebUI stays on the existing static assets and continues to submit
`docx -> latex` tasks, but the backend payloads are now served by the new platform.
