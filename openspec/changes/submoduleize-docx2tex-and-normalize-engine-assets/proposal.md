# submoduleize-docx2tex-and-normalize-engine-assets

## Why

The platform and engine refactors left one major boundary unresolved: the upstream
`docx2tex` source, engine-owned assets, and platform runtime defaults are still mixed
between the repository root, engine packages, and transitional compatibility modules.

This change normalizes those boundaries so that:

- the upstream `docx2tex` dependency is managed as a formal git submodule
- engine-local runtime assets have one canonical location
- the platform resolves default runtime paths from engine-local assets instead of the
  repository root
- `src/docx2tex_service` stops carrying implementation logic and remains only as a thin
  compatibility shell
- architecture documentation becomes authoritative and matches the real repository layout

## What Changes

- register upstream `docx2tex` as a git submodule under
  `src/engines/docx2tex_engine/vendor/docx2tex`
- move repository-owned `conf/*.xml`, `force-zh-cn-lang.xsl`, and XML catalog assets into
  `src/engines/docx2tex_engine/assets/`
- normalize Pandoc engine runtime assets under `src/engines/pandoc_engine/assets/`
- update platform runtime, local scripts, tests, Docker, and docs to resolve engine-local
  assets and vendor paths
- trim `src/docx2tex_service` down to compatibility entrypoints only

## Impact

- no new public feature is introduced
- runtime defaults for `DOCX2TEX_HOME` and `XML_CATALOG_FILES` now come from the engine
  package layout
- repository structure becomes ready for future engine additions that follow the same
  `assets / vendor / resources` contract
