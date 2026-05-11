## ADDED Requirements

### Requirement: Service exposes UI preset metadata

The service SHALL expose `GET /v1/ui/presets` to return the backend-owned whitelist of first-release WebUI presets and option values.

#### Scenario: Preset metadata returns supported UI options
- **WHEN** a client requests `GET /v1/ui/presets`
- **THEN** the service returns preset metadata including `conf_presets`, `custom_xsl_presets`, `table_models`, `math_type_sources`, and `defaults`

## MODIFIED Requirements

### Requirement: Service exposes supported conversion endpoints

The service SHALL expose the supported HTTP endpoints `GET /`, `POST /v1/task`, `GET /v1/task/{task_id}`, `GET /v1/task/{task_id}/result`, `POST /v1/dryrun`, `GET /v1/ui/presets`, `GET /healthz`, and `GET /version`.

#### Scenario: Health check succeeds
- **WHEN** a client sends `GET /healthz`
- **THEN** the service returns a JSON body with `status` equal to `ok`

#### Scenario: Version endpoint reports service identity
- **WHEN** a client sends `GET /version`
- **THEN** the service returns a JSON body containing `service` and `docx2tex_home`

### Requirement: Task submission accepts one source and supported optional inputs

The service SHALL accept exactly one task source for `POST /v1/task`: either an uploaded DOCX file or a `url` value. The service SHALL accept the optional inputs `debug`, `img_post_proc`, `conf`, `conf_preset`, `custom_xsl`, `custom_xsl_preset`, `custom_evolve`, `StyleMap`, `MathTypeSource`, `TableModel`, and `image_dir` for this endpoint. The service SHALL reject requests that provide both `conf` and `conf_preset`, or both `custom_xsl` and `custom_xsl_preset`.

#### Scenario: Uploaded DOCX creates a task
- **WHEN** a client submits `POST /v1/task` with a DOCX upload and valid optional inputs
- **THEN** the service creates a task, persists the uploaded DOCX in the task work directory, and returns `task_id`, `cache_key`, and `cache_status`

#### Scenario: URL source creates a task
- **WHEN** a client submits `POST /v1/task` with a `url` and no uploaded DOCX
- **THEN** the service downloads the DOCX into the task work directory and returns `task_id`, `cache_key`, and `cache_status`

#### Scenario: Invalid source combination is rejected
- **WHEN** a client submits `POST /v1/task` with both `file` and `url`, or with neither `file` nor `url`
- **THEN** the service returns HTTP 400

#### Scenario: Conf upload and preset conflict is rejected
- **WHEN** a client submits `POST /v1/task` with both `conf` and `conf_preset`
- **THEN** the service returns HTTP 400

#### Scenario: Custom XSL upload and preset conflict is rejected
- **WHEN** a client submits `POST /v1/task` with both `custom_xsl` and `custom_xsl_preset`
- **THEN** the service returns HTTP 400

### Requirement: Uploaded auxiliary files are normalized before use

The service SHALL persist uploaded `conf`, `custom_xsl`, and `custom_evolve` files in the task work directory using sanitized filenames. When an uploaded `conf` file imports `conf.xml` through a relative reference, the service SHALL rewrite that import to the container default configuration URI before the job is submitted. When a client supplies supported preset identifiers instead of uploads for `conf` or `custom_xsl`, the service SHALL resolve those identifiers to backend-owned repository file paths before the job is submitted.

#### Scenario: Uploaded config import is rewritten
- **WHEN** a client uploads a `conf` file that references `conf.xml` using a relative `href`
- **THEN** the saved config file contains the default configuration URI instead of the relative `conf.xml` reference

#### Scenario: Uploaded filenames are sanitized
- **WHEN** a client uploads task source or auxiliary files whose names are not safe for the pipeline
- **THEN** the service stores sanitized filenames in the task work directory before invoking the conversion flow

#### Scenario: Supported conf preset resolves to repository config
- **WHEN** a client submits `POST /v1/task` with a supported `conf_preset`
- **THEN** the service resolves that preset to the corresponding repository configuration file path before submitting the job

#### Scenario: Unsupported preset is rejected
- **WHEN** a client submits `POST /v1/task` with an unsupported `conf_preset` or `custom_xsl_preset`
- **THEN** the service returns HTTP 400
