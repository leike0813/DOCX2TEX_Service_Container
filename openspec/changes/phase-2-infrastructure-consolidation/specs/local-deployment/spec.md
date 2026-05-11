## MODIFIED Requirements

### Requirement: The Service Shall Use A Single `src`-Based Deployment Shape

The project SHALL use `pyproject.toml` and the `src/docx2tex_service/` package as the only supported deployment and runtime shape.

#### Scenario: Docker and local startup target the same app import

- **WHEN** an operator starts the service locally or in Docker
- **THEN** the app import target is `docx2tex_service.interfaces.api.app:app`
- **AND** deployment no longer depends on `app/server.py` or `app/requirements.txt`
