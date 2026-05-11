# conversion-platform Specification Delta

## ADDED Requirements

### Requirement: latex to docx pandoc preprocesses vector image assets

The platform SHALL preprocess explicit `\includegraphics` references for `latex -> docx@pandoc`
before invoking Pandoc.

#### Scenario: SVG is converted to EMF
- **WHEN** a latex workspace references an `svg` asset through `\includegraphics`
- **THEN** the platform generates an `emf` derivative and rewrites the TeX reference to it

#### Scenario: PDF or EPS falls back to PNG
- **WHEN** a `pdf` or `eps` asset cannot be converted to `emf`
- **THEN** the platform attempts a `png` fallback at `300 DPI`

#### Scenario: Failed conversion keeps the original asset
- **WHEN** vector image conversion fails and no permitted fallback succeeds
- **THEN** the task continues
- **AND** the manifest records the image conversion failure
