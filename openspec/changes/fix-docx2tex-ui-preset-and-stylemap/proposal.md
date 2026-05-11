# fix-docx2tex-ui-preset-and-stylemap

## Why

The current docx2tex WebUI exposes docx2tex profiles but does not reliably apply the
selected configuration because repository-owned preset configs are passed through without
the same import normalization logic used for uploaded configs.

The UI also omits the `StyleMap` input even though the docx2tex path already supports
StyleMap-driven evolve-driver injection.

## What Changes

- normalize docx2tex preset configs into task-local effective conf files before execution
- keep uploaded conf and profile-derived conf on the same preparation path
- add a visible StyleMap builder to the current docx2tex WebUI
- serialize StyleMap rows to the existing `StyleMap` form field on `/v2/tasks`
- add coverage for effective conf materialization and StyleMap UI submission
