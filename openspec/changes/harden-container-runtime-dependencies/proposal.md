# harden-container-runtime-dependencies

## Why

The project already checks runtime dependencies in local development, but the container image
and container entrypoint do not currently guarantee the same dependency contract. This leaves
the service in a partially usable state where the API may start while formal conversion paths
still fail later at task execution time.

## What Changes

- treat `pandoc-tex-numbering` as a formal Python runtime dependency instead of a manual extra
- make the container build fail if `docx2tex` submodule files or required binaries are missing
- make the container entrypoint run `check-system` before starting `uvicorn`
- document the stricter container and local install guarantees
