## ADDED Requirements

### Requirement: The Service Shall Support Non-Container Local Deployment

The project SHALL document and support a Linux-first local deployment path that does not require Docker.

#### Scenario: Local defaults avoid container-only paths

- **GIVEN** the service runs without explicit environment overrides
- **THEN** runtime data, public artifacts, and logs default to repository-local directories
- **AND** local import or startup does not require write access to `/data` or `/work`

#### Scenario: Operators can verify local prerequisites

- **WHEN** an operator runs the CLI system check
- **THEN** the service validates Java, Inkscape, Pandoc, `DOCX2TEX_HOME`, and `XML_CATALOG_FILES`
- **AND** the output is suitable for local troubleshooting
