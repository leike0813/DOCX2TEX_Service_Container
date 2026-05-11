# conversion-api Specification Delta

## MODIFIED Requirements

### Requirement: Service exposes matrix-aware platform endpoints

The service SHALL expose `GET /v1/capabilities`, `GET /v1/profiles`, `POST /v2/tasks`,
`GET /v2/tasks/{task_id}`, `GET /v2/tasks/{task_id}/result`, `POST /v2/dryrun`,
`GET /healthz`, and `GET /version`.

#### Scenario: Task submission is profile-driven
- **WHEN** a client submits `POST /v2/tasks`
- **THEN** the client provides `source_format`, `target_format`, and `profile_id`
- **AND** the service resolves the path and engine from the selected profile

#### Scenario: Latex to docx uses pandoc workspace zip input
- **WHEN** a client submits a `latex -> docx` task
- **THEN** the uploaded source is a ZIP workspace
- **AND** the task optionally accepts `main_tex`
- **AND** the result remains downloadable as a ZIP archive

#### Scenario: Capabilities reflect the matrix
- **WHEN** a client requests `GET /v1/capabilities`
- **THEN** the response contains matrix cells, not just a flat direction list

#### Scenario: Profiles are grouped by path
- **WHEN** a client requests `GET /v1/profiles`
- **THEN** the response groups profiles by conversion path
- **AND** also returns compatibility defaults for the existing docx-to-latex WebUI
