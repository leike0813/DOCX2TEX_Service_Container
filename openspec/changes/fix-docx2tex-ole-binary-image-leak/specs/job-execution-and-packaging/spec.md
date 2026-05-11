# job-execution-and-packaging Specification Delta

## MODIFIED Requirements

### Requirement: docx2tex debug and release bundles preserve diagnostics without leaking OLE binaries

The packaging layer SHALL keep raw OLE diagnostics in debug artifacts while removing OLE binary
references from final TeX and release image outputs.

#### Scenario: Debug bundles retain raw diagnostics
- **WHEN** a docx2tex task runs in debug mode with embedded OLE objects
- **THEN** the packaged final TeX comments out uncompilable OLE binary references
- **AND** the raw debug directories may still contain the original `.bin` assets for diagnosis

#### Scenario: Built-in profiles suppress OLE binary placeholders early
- **WHEN** built-in docx2tex conf presets transform `OLEObject` media entries
- **THEN** those presets do not emit `\includegraphics` commands for `.bin` placeholders
