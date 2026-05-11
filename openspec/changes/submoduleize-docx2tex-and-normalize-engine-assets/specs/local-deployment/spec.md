# local-deployment Specification Delta

## MODIFIED Requirements

### Requirement: Default runtime paths come from engine-local vendor and asset resolvers

Local deployment and container deployment SHALL derive default `docx2tex` runtime paths
from the normalized engine package layout.

#### Scenario: default docx2tex home uses the engine vendor path
- **WHEN** `DOCX2TEX_HOME` is not explicitly provided
- **THEN** the platform uses `src/engines/docx2tex_engine/vendor/docx2tex` as the default upstream home

#### Scenario: default XML catalog is generated from the engine asset template
- **WHEN** `XML_CATALOG_FILES` is not explicitly provided
- **THEN** the platform resolves an XML catalog from `src/engines/docx2tex_engine/assets/xmlcatalog/`
- **AND** the resolved catalog points to the effective upstream vendor path

#### Scenario: container build uses the checked-in submodule
- **WHEN** the Docker image is built
- **THEN** the image copies the checked-in `docx2tex` submodule and engine assets
- **AND** does not clone upstream `docx2tex` during the build
