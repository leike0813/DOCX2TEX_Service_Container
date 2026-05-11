## MODIFIED Requirements

### Requirement: The Service Shall Resolve Converters Through A Fully Consolidated Platform Runtime

The service SHALL run through a platform runtime assembled entirely from `src/docx2tex_service/` components.

#### Scenario: Platform runtime no longer depends on legacy app modules

- **GIVEN** the platform runtime is built
- **THEN** configuration, persistence, cache coordination, execution, packaging, and maintenance are resolved from `src/docx2tex_service/infrastructure/`
- **AND** the runtime does not import `app.core.*` or `app.services.*`
