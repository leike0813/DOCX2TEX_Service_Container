# local-deployment Specification Delta

## ADDED Requirements

### Requirement: Container image includes the formal runtime dependency set

The container image SHALL install the formal runtime dependencies required by the currently
supported conversion paths, including `pandoc-tex-numbering` for `latex -> docx@pandoc`.

#### Scenario: Container build fails when the submodule runtime is absent
- **WHEN** the container image is built without an initialized `docx2tex` submodule checkout
- **THEN** the build fails before producing an image

#### Scenario: Container build fails when a required runtime binary is absent
- **WHEN** the container image is missing one of the required runtime commands
- **THEN** the build fails before producing an image

### Requirement: Container startup performs dependency self-checks

The container entrypoint SHALL run the same dependency self-check used by local deployment
before starting the HTTP server.

#### Scenario: Missing dependency blocks startup
- **WHEN** the entrypoint runs and `check-system` reports a missing dependency
- **THEN** the container exits with a non-zero status

#### Scenario: Healthy runtime starts the service
- **WHEN** the entrypoint runs and `check-system` succeeds
- **THEN** the entrypoint starts the API server
