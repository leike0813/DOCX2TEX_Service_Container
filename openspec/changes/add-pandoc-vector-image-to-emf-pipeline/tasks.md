## 1. Change Setup

- [x] 1.1 Create the `add-pandoc-vector-image-to-emf-pipeline` change artifacts.

## 2. Pandoc Image Preprocessing

- [x] 2.1 Add a Pandoc LaTeX preprocessor that scans explicit `\\includegraphics` references and converts `svg/pdf/eps` assets.
- [x] 2.2 Extend Pandoc orchestration and manifests to carry image conversion summaries and generated files.

## 3. Validation

- [x] 3.1 Add unit/integration/E2E coverage for vector image conversion and fallback behavior.
- [x] 3.2 Run `pytest`, `mypy`, `ruff`, and strict OpenSpec validation.
