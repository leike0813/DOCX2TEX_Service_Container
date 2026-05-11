# conversion-platform Specification Delta

## ADDED Requirements

### Requirement: Platform exposes a path × engine capability matrix

The platform SHALL model conversion support as capability cells keyed by conversion path
and engine, rather than treating one direction as one implementation.

#### Scenario: Matrix payload lists implemented and planned cells
- **WHEN** a client requests platform capabilities
- **THEN** the response includes the cells `docx_to_latex@docx2tex`,
  `docx_to_latex@pandoc`, `latex_to_docx@pandoc`, and `latex_to_markdown@pandoc`
- **AND** each cell includes `path_id`, `engine_id`, and `status`

### Requirement: Profiles are path-scoped and engine-backed

The platform SHALL resolve user-facing profiles within a conversion path and SHALL map
each profile to exactly one engine implementation.

#### Scenario: Profile resolves engine for a path
- **WHEN** a task is submitted with `source_format`, `target_format`, and `profile_id`
- **THEN** the platform resolves the conversion path from the source and target formats
- **AND** resolves the selected profile within that path
- **AND** dispatches the task to the profile's bound engine
