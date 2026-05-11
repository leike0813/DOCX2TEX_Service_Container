# Design

## Resource Model

Pandoc route resources are split into two groups:

- repository-owned text assets:
  - numbering metadata
  - CSL
  - Lua filters
- runtime-materialized assets:
  - reference-doc `.docx`

Reference docs are generated on demand into the runtime directory so the repository does not
need to store binary Word templates directly.

## Request Assembly

`latex -> docx@pandoc` keeps `profile_id` as the path-scoped entrypoint, but the request can
override:

- `reference_doc_id`
- `numbering_metadata_id`
- `lua_filter_ids`
- `exec_filter_ids`
- `top_level_division`
- `citeproc`
- `csl_id`
- `bibliography_paths`
- `main_tex`

Profile defaults are resolved first, then explicit request values override them. For the
`pandoc-auto` profile, template detection can still refine the default `reference_doc_id`
and `top_level_division`.

## Bibliography Rules

The uploaded ZIP is treated as a LaTeX workspace. Bibliography follows a narrow rule set:

- if `citeproc=false`, bibliography and CSL are ignored
- if `citeproc=true` and `bibliography_paths` is empty, all `.bib` files in the workspace
  are auto-discovered
- if `bibliography_paths` is provided, each path must stay inside the extracted workspace

## WebUI

The WebUI becomes path-aware. It keeps the current docx2tex controls, and adds a second
route form for `latex -> docx@pandoc` with ZIP upload plus Pandoc option selectors.
