# local-deployment Specification Delta

## MODIFIED Requirements

### Requirement: Local entrypoints target the platform package

The local deployment and CLI entrypoints SHALL start the service through
`document_conversion`, while compatibility shims remain available for transitional use.

#### Scenario: Local deploy script starts the new platform entrypoint
- **WHEN** the user runs the local deployment script or the Python CLI
- **THEN** the underlying service process starts from `document_conversion`
