## MODIFIED Requirements

### Requirement: The Conversion API Shall Expose Only The Platform Task Surface

The API SHALL expose the platform endpoints as the only supported task submission and retrieval surface.

#### Scenario: Platform endpoints remain available

- **WHEN** a client requests `GET /v1/capabilities` or `GET /v1/profiles`
- **THEN** the service responds successfully with platform capability and profile metadata

- **WHEN** a client submits `POST /v2/tasks`
- **THEN** the service accepts the platform task model and dispatches through the converter registry

- **WHEN** a client submits `POST /v2/dryrun`
- **THEN** the service returns a dry-run artifact ZIP when effective XSL generation succeeds

#### Scenario: Removed legacy endpoints are not served

- **WHEN** a client requests any of `POST /v1/task`, `GET /v1/task/{task_id}`, `GET /v1/task/{task_id}/result`, `GET /v1/ui/presets`, or `POST /v1/dryrun`
- **THEN** the service returns `404 Not Found`
