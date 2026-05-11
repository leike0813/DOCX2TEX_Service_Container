## 1. OpenSpec And Engine Asset Skeleton

- [x] 1.1 Create the `submoduleize-docx2tex-and-normalize-engine-assets` change artifacts.
- [x] 1.2 Add engine-local asset resolution helpers for `docx2tex_engine` and normalize Pandoc asset paths.

## 2. Runtime And Build Path Normalization

- [x] 2.1 Repoint platform runtime defaults, CLI, Docker, and local scripts to engine-local vendor and asset paths.
- [x] 2.2 Update `docx2tex` runner, presets, dry-run, and related helpers to resolve conf and XML catalog paths from the engine package layout.

## 3. Compatibility And Repository Cleanup

- [x] 3.1 Trim `src/docx2tex_service` down to a thin compatibility shell and move WebUI assets to the platform package.
- [x] 3.2 Remove repository-root runtime asset assumptions and update tests to import from `document_conversion` and `engines.*`.

## 4. Documentation And Validation

- [x] 4.1 Rewrite `docs/architecture.md` as the authoritative package and asset boundary document, and update related docs to the new submodule paths.
- [x] 4.2 Run `git submodule status`, `pytest`, `mypy`, `ruff`, and strict OpenSpec validation.
