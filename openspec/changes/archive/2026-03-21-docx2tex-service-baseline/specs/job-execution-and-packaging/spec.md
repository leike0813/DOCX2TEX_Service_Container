## ADDED Requirements

### Requirement: Conversion jobs execute asynchronously through persisted task state

The service SHALL create each submitted task in a persisted `pending` state and SHALL execute conversion work asynchronously through the job manager thread pool. During execution, the service SHALL advance task state through `running`, `converting`, and `packaging`, and SHALL finish in either `done` or `failed`.

#### Scenario: Submitted task starts as pending
- **WHEN** the service accepts a new conversion request
- **THEN** it persists a task record with state `pending` and a dedicated work directory

#### Scenario: Successful job reaches done
- **WHEN** background execution completes conversion and packaging without error
- **THEN** the persisted task state becomes `done`

#### Scenario: Failed job reaches failed
- **WHEN** conversion or packaging raises an unrecovered error
- **THEN** the persisted task state becomes `failed` and stores an error message

### Requirement: Job execution invokes the bundled docx2tex pipeline

The job manager SHALL invoke the bundled Calabash launcher against the upstream `docx2tex.xpl` pipeline using the task work directory as the source of saved inputs. The invocation SHALL pass the selected configuration, optional effective evolve driver, optional custom XSL, debug toggle, debug directory URI, and pipeline outputs for TeX and Hub XML.

#### Scenario: Default configuration is used when no conf file is uploaded
- **WHEN** a task is submitted without an uploaded `conf`
- **THEN** the job manager uses the container's default `conf.xml` path when constructing the Calabash command

#### Scenario: Effective evolve driver is used when present
- **WHEN** a task request produces or uploads a custom evolve driver
- **THEN** the job manager passes that file through the `custom-evolve-hub-driver` input port during pipeline invocation

#### Scenario: Pipeline failure aborts the job
- **WHEN** the Calabash process returns a non-zero exit code or no TeX output file is produced
- **THEN** the service marks the task as `failed` and does not publish the job as a successful result

### Requirement: Non-debug packaging publishes TeX and collected images

For tasks with `debug=false`, the service SHALL package the main TeX file and the collected image directory into a ZIP in the public work directory, and SHALL include a `manifest.json` that lists the packaged files.

#### Scenario: Non-debug ZIP contains TeX and image artifacts
- **WHEN** a non-debug job completes successfully
- **THEN** the public ZIP contains the main `.tex` file and any files present in the configured image directory

#### Scenario: Non-debug packaging fails without TeX output
- **WHEN** non-debug packaging is reached and the main TeX file does not exist
- **THEN** the service marks the task as `failed`

### Requirement: Debug packaging publishes intermediate artifacts

For tasks with `debug=true`, the service SHALL package the main TeX file, Hub XML, optional CSV, debug directory contents, extracted DOCX temporary directory contents, task log, and any generated effective evolve-driver or StyleMap manifest into the public ZIP. The ZIP SHALL include a `manifest.json` that lists the packaged files.

#### Scenario: Debug ZIP includes core debug artifacts
- **WHEN** a debug job completes successfully
- **THEN** the public ZIP contains the main `.tex`, `.xml`, and `manifest.json`

#### Scenario: Debug ZIP includes optional generated artifacts
- **WHEN** the task work directory contains `custom-evolve-effective.xsl` or `stylemap_manifest.json`
- **THEN** the debug ZIP includes those artifacts
