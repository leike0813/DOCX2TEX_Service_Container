## ADDED Requirements

### Requirement: Service provides an integrated browser entry point

The service SHALL expose `GET /` as a browser-accessible WebUI entry point served by the existing FastAPI process.

#### Scenario: Browser loads the WebUI
- **WHEN** a user opens `/` in a browser
- **THEN** the service returns the integrated WebUI page instead of requiring a separate frontend runtime

### Requirement: WebUI supports drag-and-drop DOCX submission

The WebUI SHALL allow the user to provide exactly one `.docx` file through a drag-and-drop upload area and SHALL also provide a click-to-select fallback.

#### Scenario: User drops a DOCX file
- **WHEN** the user drops a single `.docx` file onto the upload area
- **THEN** the page accepts that file as the pending submission source

#### Scenario: User drops an unsupported file
- **WHEN** the user drops a file that does not end with `.docx`
- **THEN** the page shows a validation error and does not submit the file

### Requirement: WebUI exposes first-release conversion controls

The WebUI SHALL render a `debug` toggle and dropdowns for repository-supported `conf`, `custom_xsl`, `TableModel`, and `MathTypeSource` options. The first release SHALL expose only backend-provided presets and SHALL not expose URL submission, custom uploads, `custom_evolve`, `FontMapsZip`, Dry-run UI, or free-form StyleMap editing.

#### Scenario: Page loads supported dropdown options
- **WHEN** the WebUI initializes
- **THEN** it renders the supported option sets returned by the backend preset metadata endpoint

#### Scenario: Unsupported first-release controls are absent
- **WHEN** the user views the first-release WebUI
- **THEN** the page does not present URL submission, custom config upload, or Dry-run controls

### Requirement: WebUI submits jobs and reflects task progress

The WebUI SHALL submit the selected DOCX and first-release options to the existing task submission flow, display the returned `task_id`, poll task status every 2 seconds, and stop polling when the task reaches `done` or `failed`.

#### Scenario: Successful submission starts polling
- **WHEN** the user submits a valid conversion request from the page
- **THEN** the page shows the returned `task_id` and begins polling the task status endpoint

#### Scenario: Failed task surfaces the error
- **WHEN** a polled task reaches `failed`
- **THEN** the page displays the backend error message and stops polling

### Requirement: WebUI exposes result download for completed tasks

The WebUI SHALL present a download action only after a task reaches `done`, and that action SHALL download the ZIP produced by the existing result endpoint.

#### Scenario: Completed task enables download
- **WHEN** the polled task state becomes `done`
- **THEN** the page enables a download action that targets `GET /v1/task/{task_id}/result`
