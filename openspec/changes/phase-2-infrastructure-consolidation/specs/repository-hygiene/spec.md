## ADDED Requirements

### Requirement: The Repository Shall Keep Active Assets Separate From Runtime And Legacy Noise

The repository SHALL remove generated runtime outputs, transitional implementation shells, and abandoned prototype assets from the active project surface.

#### Scenario: Runtime outputs are not tracked as active project content

- **THEN** generated directories such as `.local`, `result`, `result_debug`, and `tmpdata` are treated as runtime artifacts
- **AND** tool caches such as `.mypy_cache`, `.pytest_cache`, and `.ruff_cache` are not part of the maintained source tree

#### Scenario: Legacy implementation shells are removed

- **THEN** old Python implementation files under `app/` are no longer part of the maintained service implementation
- **AND** historical experiments are either removed from the main layout or left recoverable through repository history
