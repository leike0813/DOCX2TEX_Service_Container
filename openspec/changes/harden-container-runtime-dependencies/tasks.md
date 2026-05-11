## 1. Change Setup

- [x] 1.1 Create the `harden-container-runtime-dependencies` change artifacts.

## 2. Runtime Dependency Guarantee

- [x] 2.1 Add `pandoc-tex-numbering` to the formal Python runtime dependency set.
- [x] 2.2 Make the Docker build fail when the `docx2tex` submodule or required runtime binaries are missing.
- [x] 2.3 Make the container entrypoint run dependency checks before starting the API server.

## 3. Validation And Docs

- [x] 3.1 Add deployment-side tests for `check-system` and the fail-fast entrypoint behavior.
- [x] 3.2 Update README and local deployment docs to reflect the new dependency contract.
- [x] 3.3 Run `pytest`, `mypy`, `ruff`, and strict OpenSpec validation.
