# cache-and-postprocess Specification Delta

## MODIFIED Requirements

### Requirement: docx2tex release packaging emits compilable image references

The docx2tex postprocess and packaging path SHALL keep uncompilable OLE binary image references
out of final TeX and release bundles.

#### Scenario: OLE binary references are commented instead of emitted
- **WHEN** the final TeX contains `\includegraphics` that targets an OLE `.bin` payload
- **THEN** the platform comments out that reference with an explanatory note
- **AND** the task continues to produce a compilable TeX file

#### Scenario: OLE binary assets are skipped from release image bundles
- **WHEN** release packaging collects referenced image assets
- **THEN** `oleObject*.bin` files are not copied into the final image directory
- **AND** the manifest records the skipped OLE binary assets
