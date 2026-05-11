## 1. OpenSpec And Package Skeleton

- [x] 1.1 Create the `rebuild-platform-around-capability-matrix` change artifacts.
- [x] 1.2 Add the new `src/document_conversion/`, `src/engines/docx2tex_engine/`, and `src/engines/pandoc_engine/` package skeletons.

## 2. Matrix Platform

- [x] 2.1 Replace direction-only registry logic with a path × engine capability matrix.
- [x] 2.2 Make profiles path-scoped and resolve tasks by `profile_id -> path -> engine`.
- [x] 2.3 Move API and CLI entrypoints to `document_conversion` and keep `docx2tex_service` as a compatibility shell.

## 3. Engine Integration

- [x] 3.1 Connect the current `docx -> latex` path as `docx_to_latex@docx2tex`.
- [x] 3.2 Absorb the external Pandoc pipeline skeleton into `pandoc_engine`.
- [x] 3.3 Implement `docx_to_latex@pandoc` and `latex_to_docx@pandoc`.

## 4. Documentation And Validation

- [x] 4.1 Update docs and local entrypoints for the new package layout.
- [x] 4.2 Update tests to validate the matrix model and the Pandoc path.
- [x] 4.3 Run `pytest`, `mypy`, `ruff`, and strict OpenSpec validation.
