## 1. Change Foundation

- [x] 1.1 Add the proposal for the integrated WebUI and link it to the new `integrated-web-ui` capability plus the `conversion-api` delta.
- [x] 1.2 Add spec artifacts that define the UI surface and the preset-aware conversion API extensions.

## 2. Backend API Support

- [x] 2.1 Add backend preset definitions for the supported `conf` and `custom_xsl` options and expose them through `GET /v1/ui/presets`.
- [x] 2.2 Extend `POST /v1/task` to accept `conf_preset` and `custom_xsl_preset`, validate mutual exclusion with uploaded files, and resolve preset identifiers to repository file paths.

## 3. Integrated UI

- [x] 3.1 Add a page served from `GET /` that renders the first-release upload form and Chinese UI copy.
- [x] 3.2 Implement drag-and-drop DOCX upload, `debug` toggle, preset dropdowns, task submission, status polling, and ZIP download behavior in the page JavaScript.

## 4. Verification

- [x] 4.1 Add tests for the page route, preset metadata route, preset-aware task submission, and conflict/error validation.
- [x] 4.2 Verify that the integrated UI does not regress existing `/v1/task`, `/healthz`, `/version`, and result download behavior.
