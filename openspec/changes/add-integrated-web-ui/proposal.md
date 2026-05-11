## Why

The service currently exposes only programmatic HTTP endpoints, which makes common document conversion flows awkward for users who just need to upload a DOCX, toggle a small set of options, and download the resulting ZIP. A first integrated WebUI is needed so the container can present a usable browser-based entry point without introducing a second deployment unit.

## What Changes

- Add a first-party WebUI served by the existing FastAPI process at `/`.
- Extend the conversion API so UI users can submit jobs using server-side preset identifiers instead of uploading repository-bundled config files.
- Add a UI preset metadata endpoint so the page can render supported dropdown options from backend-controlled data.
- Keep the first release intentionally narrow: single DOCX upload, drag-and-drop interaction, `debug` toggle, built-in preset selection, task status polling, and ZIP download.
- Exclude URL submission, custom config uploads, `FontMapsZip`, `/v1/nocache`, Dry-run UI, and free-form StyleMap editing from this change.

## Capabilities

### New Capabilities
- `integrated-web-ui`: Browser-based upload and download flow served directly by the current FastAPI service.

### Modified Capabilities
- `conversion-api`: Extend the task submission surface to accept built-in preset identifiers and expose UI preset metadata.

## Impact

- Affects the FastAPI application routing surface, including a new page endpoint and a new UI metadata API.
- Requires backend mapping for repository-bundled config/XSL presets used by the WebUI.
- Adds OpenSpec artifacts for the new UI capability and for conversion API deltas without changing the current job execution or cache contracts.
