## 1. Change Setup

- [x] 1.1 Create the `fix-docx2tex-ui-preset-and-stylemap` change artifacts.

## 2. docx2tex Config Handling

- [x] 2.1 Make profile-selected docx2tex preset configs materialize into task-local effective conf files.
- [x] 2.2 Reuse the same effective-conf preparation path for uploaded and preset configs.

## 3. WebUI StyleMap Support

- [x] 3.1 Add a visible StyleMap row builder to the docx2tex WebUI.
- [x] 3.2 Serialize StyleMap rows to the existing `StyleMap` task field and keep current task polling/download behavior.

## 4. Validation

- [x] 4.1 Add API/WebUI coverage for effective conf materialization and StyleMap submission.
- [x] 4.2 Run `pytest`, `mypy`, `ruff`, and strict OpenSpec validation.
