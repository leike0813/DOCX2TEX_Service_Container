# Design

## Dependency Contract

Container runtime dependencies are split into two classes:

- system packages installed by Debian package manager:
  - `java`
  - `inkscape`
  - `pandoc`
- Python-installed runtime commands:
  - `pandoc-tex-numbering`

The service treats all of them as required for the set of formally supported paths.

## Build-Time Validation

The Docker build performs two kinds of checks:

- repository layout checks:
  - `DOCX2TEX_HOME/xpl/docx2tex.xpl` must exist, which proves the submodule has been initialized
- runtime dependency checks:
  - the same `check-system` command used locally must succeed inside the image

This keeps the image contract aligned with the documented runtime contract.

## Startup Behavior

The container entrypoint becomes strict fail-fast:

- export runtime paths
- run `python -m document_conversion.interfaces.cli check-system`
- only start `uvicorn` if that command succeeds

No bypass or degraded mode is added in this change.
