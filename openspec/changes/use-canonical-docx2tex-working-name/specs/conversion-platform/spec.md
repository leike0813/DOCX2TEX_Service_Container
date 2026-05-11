## MODIFIED Requirements

### Requirement: docx2tex tasks use a canonical internal DOCX name

The platform SHALL persist each `docx -> latex@docx2tex` source document as a fixed
internal filename `input.docx`, while recording the original filename and display
basename separately in task metadata.

#### Scenario: Uploaded DOCX is stored with canonical internal name

- **WHEN** a client uploads a DOCX named `安全报告.docx`
- **THEN** the task work directory contains the source as `input.docx`
- **AND** task metadata records `original_filename` as `安全报告.docx`
- **AND** task metadata records `internal_basename` as `input`

#### Scenario: URL DOCX is stored with canonical internal name

- **WHEN** a client submits a DOCX URL whose path basename is `报告.docx`
- **THEN** the downloaded source is stored as `input.docx`
- **AND** task metadata records the URL basename as the original filename

### Requirement: docx2tex cache keys ignore user-facing filenames

The platform SHALL compute docx2tex cache keys from `input.docx` bytes and
conversion-affecting options, not from the submitted original filename.

#### Scenario: Same content with different filenames reuses cache

- **WHEN** two docx2tex tasks submit identical DOCX bytes with different original filenames
- **THEN** they compute the same cache key
- **AND** each task still publishes its own user-facing result name
