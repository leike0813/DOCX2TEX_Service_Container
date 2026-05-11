# conversion-platform Specification Delta

## MODIFIED Requirements

### Requirement: Platform separates engine-owned vendor code, runtime assets, and resources

The platform SHALL keep each engine's upstream source, repository-owned runtime assets,
and non-runtime reference materials in distinct locations.

#### Scenario: docx2tex upstream source is engine-local vendor code
- **WHEN** the platform resolves the upstream `docx2tex` dependency
- **THEN** it uses `src/engines/docx2tex_engine/vendor/docx2tex`
- **AND** the repository root `docx2tex/` directory is not treated as the runtime source of truth

#### Scenario: engine profiles resolve repository-owned assets
- **WHEN** the platform resolves `docx2tex` profile presets or engine-local XML catalog assets
- **THEN** it uses files under `src/engines/docx2tex_engine/assets/`

### Requirement: Compatibility package is limited to public forwarding entrypoints

The legacy `docx2tex_service` package SHALL remain only as a compatibility shell for
public entrypoints and SHALL not own active platform or engine implementations.

#### Scenario: compatibility imports forward to the platform
- **WHEN** a client imports the legacy API or CLI entrypoints
- **THEN** those modules forward to `document_conversion`
- **AND** platform logic is not implemented under `src/docx2tex_service`
