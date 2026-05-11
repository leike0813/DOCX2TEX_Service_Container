# solidify-pandoc-latex-to-docx-pipeline

## Why

The current `latex -> docx@pandoc` route can submit and produce a DOCX, but it still lacks
a formal runtime model for `pandoc-tex-numbering`, built-in reference docs, numbering
metadata, CSL assets, and explicit user-facing pipeline overrides.

The current WebUI is also still centered on `docx -> latex`, so the Pandoc reverse route is
not exposed as a first-class path.

## What Changes

- add a built-in resource layer for Pandoc reference docs, numbering metadata, CSL files,
  Lua filters, and executable filters
- make `latex -> docx@pandoc` resolve profile defaults and explicit request overrides
- treat ZIP uploads as LaTeX workspaces only, with `.bib` as the only auto-discovered
  control-side resource
- extend `POST /v2/tasks` and `GET /v1/profiles` for Pandoc route options
- upgrade the WebUI into a path-aware form that supports both `docx -> latex` and
  `latex -> docx`
- add validation and coverage for command assembly, bibliography resolution, and missing
  `pandoc-tex-numbering`
