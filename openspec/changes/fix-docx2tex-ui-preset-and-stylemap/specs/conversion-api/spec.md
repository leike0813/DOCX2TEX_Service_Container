# conversion-api Specification Delta

## MODIFIED Requirements

### Requirement: docx2tex task submission applies selected config presets consistently

The service SHALL prepare docx2tex configuration overrides consistently whether they come
from uploaded config files or from selected repository-owned presets.

#### Scenario: Profile-selected preset becomes an effective conf
- **WHEN** a client submits `POST /v2/tasks` for `docx -> latex@docx2tex` with a selected profile
- **THEN** the service materializes a task-local effective conf file before starting execution
- **AND** rewrites relative `conf.xml` imports to the upstream default conf URI

#### Scenario: Uploaded conf follows the same normalization path
- **WHEN** a client submits `POST /v2/tasks` with an uploaded `conf`
- **THEN** the service prepares an effective conf file using the same normalization logic

### Requirement: docx2tex UI can submit StyleMap data

The service SHALL continue accepting the existing `StyleMap` field on `POST /v2/tasks`
for the docx2tex route.

#### Scenario: StyleMap submission produces effective evolve artifacts
- **WHEN** a client submits `POST /v2/tasks` with a non-empty `StyleMap`
- **THEN** the service prepares an effective evolve driver for the task work directory
