## ADDED Requirements

### Requirement: The Project Shall Maintain A Layered Test Suite

The repository SHALL organize tests by responsibility so platform logic, integration wiring, API behavior, and slow end-to-end coverage can evolve independently.

#### Scenario: Layered test directories exist

- **THEN** the repository contains `tests/unit`, `tests/integration`, `tests/api`, and `tests/e2e`
- **AND** slow end-to-end coverage is explicitly marked instead of always running by default

#### Scenario: Compatibility regressions remain covered during migration

- **GIVEN** the new layered tests exist
- **THEN** legacy route tests continue to verify `/v1/task` behavior until the old surface can be retired
