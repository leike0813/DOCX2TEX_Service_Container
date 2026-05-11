# test-architecture Specification Delta

## MODIFIED Requirements

### Requirement: Tests validate matrix resolution and engine separation

The test suite SHALL validate the capability matrix, path-scoped profile resolution, and
separate engine implementations.

#### Scenario: Matrix registry is unit-tested
- **WHEN** unit tests run
- **THEN** they verify path × engine cell registration and profile resolution

#### Scenario: Pandoc engine path is covered
- **WHEN** integration and API tests run
- **THEN** they verify `latex -> docx@pandoc` workspace ZIP handling and
  `docx -> latex@pandoc` task submission
