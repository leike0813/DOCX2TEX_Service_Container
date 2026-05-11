## 1. Change Setup

- [x] 1.1 Create the `solidify-pandoc-latex-to-docx-pipeline` change artifacts.

## 2. Pandoc Resource Model

- [x] 2.1 Add built-in Pandoc resource registration for reference docs, numbering metadata, CSL, Lua filters, and executable filters.
- [x] 2.2 Make `latex -> docx@pandoc` resolve profile defaults and explicit request overrides through that resource layer.

## 3. API And WebUI

- [x] 3.1 Extend `POST /v2/tasks` and `GET /v1/profiles` for Pandoc route options.
- [x] 3.2 Upgrade the WebUI into a path-aware submission form with `latex -> docx` support.

## 4. Validation

- [x] 4.1 Add unit/API/E2E coverage for Pandoc option assembly, bibliography handling, and missing executable filters.
- [x] 4.2 Run `pytest`, `mypy`, `ruff`, and strict OpenSpec validation.
