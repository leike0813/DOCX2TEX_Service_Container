## ADDED Requirements

### Requirement: The Service Shall Expose A Platform Conversion Model

The service SHALL define platform-level conversion types that are independent of a single converter implementation.

#### Scenario: Platform models are available for multiple directions

- **GIVEN** the platform package is imported
- **THEN** it defines source and target document formats
- **AND** it defines conversion directions for `docx_to_latex`, `latex_to_docx`, and `latex_to_markdown`
- **AND** it defines shared request, job, profile, and converter abstractions

### Requirement: The Service Shall Resolve Converters Through A Registry

The service SHALL select a converter by conversion direction rather than by route-specific code paths.

#### Scenario: Implemented and planned converters coexist

- **GIVEN** the platform runtime is built
- **THEN** it registers the implemented `docx2tex` converter for `docx_to_latex`
- **AND** it registers placeholder converter entries for planned pandoc-backed directions
- **AND** capability discovery reports which directions are implemented versus planned
