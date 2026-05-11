# integrated-web-ui Specification Delta

## MODIFIED Requirements

### Requirement: WebUI supports both formal submission paths

The built-in WebUI SHALL expose both the current `docx -> latex` form and a new
`latex -> docx@pandoc` form in the same page.

#### Scenario: User switches from docx route to pandoc route
- **WHEN** a user changes the conversion path selector
- **THEN** the page swaps the visible form controls and file expectations for that path

#### Scenario: User submits a latex workspace with Pandoc options
- **WHEN** a user uploads a ZIP workspace and configures Pandoc options
- **THEN** the front end serializes those options to `POST /v2/tasks`
- **AND** continues to reuse the existing task polling and result download flow
