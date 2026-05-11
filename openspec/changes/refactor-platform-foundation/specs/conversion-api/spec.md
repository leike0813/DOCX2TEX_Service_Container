## MODIFIED Requirements

### Requirement: The Conversion API Shall Support Platform-Native Task Submission

The API SHALL expose platform-level task submission and discovery endpoints alongside compatibility routes.

#### Scenario: Clients query platform capabilities and profiles

- **WHEN** a client requests `GET /v1/capabilities`
- **THEN** the service returns supported conversion directions
- **AND** each direction includes a status such as `implemented` or `planned`

- **WHEN** a client requests `GET /v1/profiles`
- **THEN** the service returns platform-level conversion profiles and option presets

#### Scenario: Clients submit a platform-native task

- **WHEN** a client submits `POST /v2/tasks` for `docx -> latex`
- **THEN** the request is mapped to the platform conversion model
- **AND** the request is dispatched through the converter registry

#### Scenario: Compatibility routes remain available

- **WHEN** a client submits `POST /v1/task`
- **THEN** the service accepts the legacy form fields
- **AND** internally maps the request to the same platform service used by `/v2/tasks`

#### Scenario: Removed cache-bypass route is explicitly rejected

- **WHEN** a client submits `POST /v1/nocache`
- **THEN** the service responds with `410 Gone`
- **AND** indicates that the route has been removed during the platform refactor
