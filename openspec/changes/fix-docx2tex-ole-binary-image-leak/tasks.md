## 1. Change Setup

- [x] 1.1 Create the `fix-docx2tex-ole-binary-image-leak` change artifacts.

## 2. OLE Binary Cleanup

- [x] 2.1 Suppress built-in docx2tex profile emission of OLE `.bin` image references.
- [x] 2.2 Comment remaining OLE `.bin` `\includegraphics` references during docx2tex TeX postprocessing.
- [x] 2.3 Exclude OLE `.bin` assets from release bundles and record cleanup summaries in the manifest.

## 3. Validation

- [x] 3.1 Add regression coverage for OLE `.bin` cleanup in postprocessing, packaging, and built-in conf assets.
- [x] 3.2 Run `pytest`, `mypy`, `ruff`, and strict OpenSpec validation.
