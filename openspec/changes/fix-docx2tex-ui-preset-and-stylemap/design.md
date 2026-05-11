# Design

## Effective Conf Preparation

The docx2tex engine already rewrites uploaded `conf.xml` imports to the upstream default
conf URI. Preset configs must go through the same normalization path or they remain
relative to the engine asset directory and can resolve imports incorrectly.

The engine will therefore materialize a task-local `effective-conf.xml` for:

- uploaded `conf`
- profile-selected preset conf

The engine continues to use the upstream default conf directly when no override is
requested.

## WebUI StyleMap Builder

The current WebUI stays single-path and docx2tex-focused. A new visible StyleMap builder
is added to the form, using rows of:

- target key
- source styles list

Rows are client-side state, serialized to the existing `StyleMap` form field as JSON.
No API contract changes are introduced.

Validation remains lightweight and client-side:

- ignore fully empty rows
- reject missing target keys
- reject rows without source styles
- reject duplicate target keys

## API And Testing

`POST /v2/tasks` remains unchanged. Tests focus on:

- preset-selected conf files becoming normalized task-local effective conf files
- StyleMap submission producing the existing effective evolve artifacts
- WebUI rendering the new StyleMap controls
