# conversion-api Specification

## Purpose
TBD - created by archiving change docx2tex-service-baseline. Update Purpose after archive.
## Requirements
### Requirement: Service exposes supported conversion endpoints

The service SHALL expose the supported HTTP endpoints `POST /v1/task`, `GET /v1/task/{task_id}`, `GET /v1/task/{task_id}/result`, `POST /v1/dryrun`, `GET /healthz`, and `GET /version`.

#### Scenario: Health check succeeds
- **WHEN** a client sends `GET /healthz`
- **THEN** the service returns a JSON body with `status` equal to `ok`

#### Scenario: Version endpoint reports service identity
- **WHEN** a client sends `GET /version`
- **THEN** the service returns a JSON body containing `service` and `docx2tex_home`

### Requirement: Task submission accepts one source and supported optional inputs

The service SHALL accept exactly one task source for `POST /v1/task`: either an uploaded DOCX file or a `url` value. The service SHALL accept the optional inputs `debug`, `img_post_proc`, `conf`, `custom_xsl`, `custom_evolve`, `StyleMap`, `MathTypeSource`, `TableModel`, and `image_dir` for this endpoint.

#### Scenario: Uploaded DOCX creates a task
- **WHEN** a client submits `POST /v1/task` with a DOCX upload and valid optional inputs
- **THEN** the service creates a task, persists the uploaded DOCX in the task work directory, and returns `task_id`, `cache_key`, and `cache_status`

#### Scenario: URL source creates a task
- **WHEN** a client submits `POST /v1/task` with a `url` and no uploaded DOCX
- **THEN** the service downloads the DOCX into the task work directory and returns `task_id`, `cache_key`, and `cache_status`

#### Scenario: Invalid source combination is rejected
- **WHEN** a client submits `POST /v1/task` with both `file` and `url`, or with neither `file` nor `url`
- **THEN** the service returns HTTP 400

### Requirement: Uploaded auxiliary files are normalized before use

The service SHALL persist uploaded `conf`, `custom_xsl`, and `custom_evolve` files in the task work directory using sanitized filenames. When an uploaded `conf` file imports `conf.xml` through a relative reference, the service SHALL rewrite that import to the container default configuration URI before the job is submitted.

#### Scenario: Uploaded config import is rewritten
- **WHEN** a client uploads a `conf` file that references `conf.xml` using a relative `href`
- **THEN** the saved config file contains the default configuration URI instead of the relative `conf.xml` reference

#### Scenario: Uploaded filenames are sanitized
- **WHEN** a client uploads task source or auxiliary files whose names are not safe for the pipeline
- **THEN** the service stores sanitized filenames in the task work directory before invoking the conversion flow

### Requirement: StyleMap dry-run generates effective XSL artifacts

The service SHALL provide `POST /v1/dryrun` to generate the effective evolve-driver artifacts produced from `StyleMap`, `conf`, and optional `custom_evolve` inputs without running a full conversion job.

#### Scenario: Dry-run returns generated artifacts
- **WHEN** a client submits `POST /v1/dryrun` with inputs that produce an effective evolve driver
- **THEN** the service returns a ZIP file containing `xsl/custom-evolve-effective.xsl`

#### Scenario: Dry-run rejects empty generation
- **WHEN** a client submits `POST /v1/dryrun` and no effective XSL artifacts are generated
- **THEN** the service returns HTTP 400

### Requirement: Task state and result endpoints reflect persisted job state

The service SHALL return persisted task state from `GET /v1/task/{task_id}` and SHALL allow result download from `GET /v1/task/{task_id}/result` only after the task state is `done`.

#### Scenario: Unknown task is not found
- **WHEN** a client requests status or result for a `task_id` that does not exist
- **THEN** the service returns HTTP 404

#### Scenario: Result download is blocked before completion
- **WHEN** a client requests `GET /v1/task/{task_id}/result` for a task whose state is not `done`
- **THEN** the service returns HTTP 409

#### Scenario: Completed task returns ZIP result
- **WHEN** a client requests `GET /v1/task/{task_id}/result` for a task whose state is `done` and whose ZIP exists in the public work directory
- **THEN** the service returns the ZIP as `application/zip`

