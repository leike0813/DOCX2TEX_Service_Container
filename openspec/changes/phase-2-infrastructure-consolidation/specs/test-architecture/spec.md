## MODIFIED Requirements

### Requirement: The Project Shall Maintain Only Layered Tests

The repository SHALL keep all active automated tests under the layered test directories.

#### Scenario: Flat legacy tests are removed

- **GIVEN** the repository test tree
- **THEN** active tests live under `tests/unit`, `tests/integration`, `tests/api`, and `tests/e2e`
- **AND** flat `tests/test_*.py` files are not part of the supported test suite
