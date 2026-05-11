# integrated-web-ui Specification Delta

## MODIFIED Requirements

### Requirement: docx2tex WebUI exposes the supported docx2tex controls

The docx2tex WebUI SHALL expose the current docx2tex profile selector, debug toggle,
custom XSL preset selector, TableModel, MathTypeSource, and a visible StyleMap builder.

#### Scenario: StyleMap builder is visible on the page
- **WHEN** a user opens the docx2tex WebUI
- **THEN** the page shows StyleMap controls without requiring a secondary navigation path

#### Scenario: StyleMap rows serialize to the existing task field
- **WHEN** a user fills StyleMap rows and submits the form
- **THEN** the front end serializes those rows into the existing `StyleMap` form field
- **AND** submits the task to `POST /v2/tasks`
