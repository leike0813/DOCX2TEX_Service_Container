## MODIFIED Requirements

### Requirement: Result downloads use recorded display filenames

The API SHALL keep the existing task submission and result endpoints unchanged, but
completed `docx -> latex@docx2tex` result downloads SHALL use the recorded display
basename for the ZIP filename.

#### Scenario: Completed task returns display-named ZIP

- **WHEN** a client uploads `安全报告.docx` and the docx2tex task completes
- **AND** the client requests `GET /v2/tasks/{task_id}/result`
- **THEN** the response is `application/zip`
- **AND** the `Content-Disposition` filename is `安全报告.zip`

### Requirement: Main DOCX filename safety is handled by service metadata

The API SHALL no longer require translating or transliterating the main DOCX upload
filename before processing. It SHALL preserve the original name as metadata and use
a service-owned canonical name for conversion.

#### Scenario: Non-ASCII upload name is accepted without transliteration

- **WHEN** a client uploads a DOCX whose filename contains non-ASCII characters
- **THEN** the request is accepted if the source is otherwise valid
- **AND** the internal conversion input name remains `input.docx`
