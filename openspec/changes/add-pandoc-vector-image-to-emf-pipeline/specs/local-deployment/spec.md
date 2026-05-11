# local-deployment Specification Delta

## MODIFIED Requirements

### Requirement: Container and local runtime include Inkscape for formal Pandoc reverse conversion

The formal `latex -> docx@pandoc` path SHALL rely on `inkscape` as the built-in converter for
vector image preprocessing.

#### Scenario: Runtime check includes Inkscape
- **WHEN** deployment checks formal runtime dependencies
- **THEN** `inkscape` is treated as required for the supported Pandoc reverse conversion path
