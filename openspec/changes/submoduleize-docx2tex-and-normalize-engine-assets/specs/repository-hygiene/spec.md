# repository-hygiene Specification Delta

## ADDED Requirements

### Requirement: Runtime assets are not maintained at the repository root

Repository-owned runtime assets SHALL live under engine packages rather than as root-level
runtime source directories.

#### Scenario: docx2tex runtime asset directories move under the engine
- **WHEN** the repository stores managed `docx2tex` profile configs or XML catalog files
- **THEN** those files live under `src/engines/docx2tex_engine/assets/`
- **AND** root-level `conf/` and `catalog/` directories are not used as runtime source directories

### Requirement: Architecture documentation is authoritative

The repository SHALL maintain a single authoritative architecture document that describes
package ownership boundaries, engine asset rules, and compatibility policy.

#### Scenario: architecture doc matches the normalized repository layout
- **WHEN** a maintainer reads `docs/architecture.md`
- **THEN** the document describes the platform package, engine packages, compatibility shell,
  submodule policy, and the `assets / vendor / resources` contract
