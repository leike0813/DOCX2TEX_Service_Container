## MODIFIED Requirements

### Requirement: docx2tex execution uses the internal basename

The job executor SHALL invoke docx2tex with the internal source filename
`input.docx`. Intermediate docx2tex outputs, cache entries, and debug directories
SHALL use the internal basename `input`.

#### Scenario: Runner receives canonical input name

- **WHEN** a docx2tex task starts conversion for any uploaded DOCX filename
- **THEN** the runner receives `input.docx` as the source name
- **AND** conversion outputs are written as `input.tex` and `input.xml`

### Requirement: Packaging publishes user-facing main artifact names

The packager SHALL publish final ZIP bundles using the display basename while keeping
internal debug directories unchanged.

#### Scenario: Non-debug package restores display basename

- **WHEN** a non-debug docx2tex task for `安全报告.docx` is packaged
- **THEN** the public ZIP is named `安全报告.zip`
- **AND** the ZIP contains `安全报告.tex`
- **AND** the manifest records `internal_basename` as `input`

#### Scenario: Debug package restores display names for main files

- **WHEN** a debug docx2tex task for `安全报告.docx` is packaged
- **THEN** the ZIP contains `安全报告.tex`
- **AND** the ZIP contains `安全报告.xml` if the XML output exists
- **AND** internal debug directories may remain named `input.debug` and `input.docx.tmp`
