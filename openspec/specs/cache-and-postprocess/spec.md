# cache-and-postprocess Specification

## Purpose
TBD - created by archiving change docx2tex-service-baseline. Update Purpose after archive.
## Requirements
### Requirement: Cache keys are derived from persisted conversion inputs

The service SHALL compute cache keys as a SHA-256 digest over the saved DOCX contents, selected configuration file contents, optional custom XSL contents, optional evolve-driver contents, selected MathType source value, selected table model value, and optional uploaded `FontMapsZip` bytes.

#### Scenario: Same effective inputs reuse the same cache key
- **WHEN** two tasks persist identical input bytes and option values for all cache-key components
- **THEN** the service computes the same cache key for both tasks

#### Scenario: Cache key changes when conversion-affecting inputs change
- **WHEN** any persisted cache-key component changes
- **THEN** the service computes a different cache key

### Requirement: Cache coordination serializes builders and restores reusable outputs

The service SHALL persist cache metadata and build locks in SQLite. When a cache entry is available, the service SHALL restore cached outputs into the task work directory instead of rebuilding them. When a cache entry is not available, the service SHALL allow only one builder to claim the cache key at a time.

#### Scenario: Ready cache entry restores outputs
- **WHEN** a task starts and its cache key already has an available cache entry
- **THEN** the service restores cached TeX, XML, CSV, debug artifacts, and extracted DOCX artifacts into the task work directory

#### Scenario: Competing builders wait on the same cache key
- **WHEN** one task has already claimed a cache lock for a cache key and another task starts with the same key
- **THEN** the later task does not start a second build while the lock is held

### Requirement: Vector and TeX post-processing runs on produced TeX output

When TeX output exists, the service SHALL optionally convert referenced `.emf`, `.wmf`, and `.svg` images to PDF and rewrite TeX references to those PDFs. During packaging, the service SHALL normalize `width=1.0\\textwidth`, `width=1\\textwidth`, `width=1.0\\linewidth`, and `width=1\\linewidth` to the normalized LaTeX width forms.

#### Scenario: Vector reference is converted to PDF
- **WHEN** TeX output references an existing `.emf`, `.wmf`, or `.svg` file and image post-processing is enabled
- **THEN** the service creates a sibling `.pdf` and rewrites the TeX reference to the PDF path

#### Scenario: Width options are normalized
- **WHEN** TeX output contains `width=1\\textwidth`, `width=1.0\\textwidth`, `width=1\\linewidth`, or `width=1.0\\linewidth`
- **THEN** the packaged TeX output uses `\\textwidth` or `\\linewidth` without the `1` multiplier

### Requirement: Packaging rewrites image references and handles VSDX differently by mode

For `debug=false`, the service SHALL collect referenced images into the configured image directory, rewrite `\\includegraphics` paths to that directory alias, and remove `.vsdx` includes from the TeX output. For `debug=true`, the service SHALL keep the debug-oriented artifact set and comment out `.vsdx` includes instead of removing them.

#### Scenario: Non-debug packaging collects images and rewrites paths
- **WHEN** non-debug packaging processes TeX that references images outside the configured image directory
- **THEN** the service copies those images into the configured image directory and rewrites the `\\includegraphics` paths to that alias

#### Scenario: Non-debug packaging removes VSDX includes
- **WHEN** non-debug packaging processes TeX that references `.vsdx` files
- **THEN** the service removes those `\\includegraphics` commands from the TeX output

#### Scenario: Debug packaging comments VSDX includes
- **WHEN** debug packaging processes TeX that references `.vsdx` files
- **THEN** the service preserves those lines as comments in the TeX output

### Requirement: StyleMap preprocessing generates an effective evolve driver

When a request provides a non-empty `StyleMap`, the service SHALL parse the JSON mapping, derive role-command associations from the selected configuration files, and write `custom-evolve-effective.xsl` in the task work directory. The service SHALL use that effective evolve driver as the request's evolve input and SHALL write `stylemap_manifest.json` for diagnostics.

#### Scenario: StyleMap request generates effective evolve artifacts
- **WHEN** a task request includes a non-empty `StyleMap` and the selected configuration yields matching role-command mappings
- **THEN** the task work directory contains `custom-evolve-effective.xsl` and `stylemap_manifest.json`

#### Scenario: StyleMap errors are rejected at request time
- **WHEN** StyleMap preprocessing raises an exception while preparing request inputs
- **THEN** the service rejects the request with HTTP 400

