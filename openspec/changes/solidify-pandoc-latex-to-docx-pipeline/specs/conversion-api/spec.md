# conversion-api Specification Delta

## MODIFIED Requirements

### Requirement: platform task submission supports explicit Pandoc route options

The platform SHALL accept explicit Pandoc route options for `latex -> docx@pandoc` task
submission while keeping `profile_id` as the path-scoped entrypoint.

#### Scenario: Pandoc route accepts built-in resource IDs
- **WHEN** a client submits `POST /v2/tasks` for `latex -> docx@pandoc`
- **THEN** the service accepts built-in IDs for reference docs, numbering metadata, Lua
  filters, executable filters, and CSL

#### Scenario: Bibliography paths must stay inside the uploaded workspace
- **WHEN** a client submits explicit `bibliography_paths`
- **THEN** each path is resolved relative to the extracted ZIP workspace
- **AND** paths outside the workspace are rejected

### Requirement: profile endpoint exposes Pandoc route options

The platform SHALL expose path-scoped Pandoc route options and defaults from `GET /v1/profiles`.

#### Scenario: Pandoc route returns resource options and defaults
- **WHEN** a client reads `GET /v1/profiles`
- **THEN** the response includes `latex_to_docx` option metadata for reference docs,
  numbering metadata, Lua filters, executable filters, CSL, and top-level-division
