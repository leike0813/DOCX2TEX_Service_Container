# Design

## Current State

`docx2tex_engine.converter` currently derives a saved DOCX filename from the upload
or URL, then passes that name through `sanitize_filename()`. The resulting basename
drives docx2tex input, output `.tex/.xml/.csv`, debug directories, cache restore
renaming, packaging, task metadata `result_name`, and result download filename.

This couples user-facing names to docx2tex's filesystem constraints and keeps a
large Chinese translation/transliteration helper in the runtime path.

## Target State

The docx2tex engine will use a fixed internal source filename:

- `internal_filename`: `input.docx`
- `internal_basename`: `input`

The user-facing identity will be separately recorded:

- `original_filename`: the upload filename or URL basename, when available
- `display_basename`: a path-safe basename derived from `original_filename`, keeping
  Unicode characters but removing path separators and control characters
- `result_name`: `<display_basename>.zip`

The runner, cache, and intermediate artifacts operate only on `input`. The packager
receives an optional display basename and writes user-facing main artifact names into
the ZIP without renaming internal working directories.

## Data Flow

1. Request preparation creates a task work directory.
2. If the source is an upload, bytes are written to `work/input.docx`.
3. If the source is a URL, bytes are downloaded to `work/input.docx`; the URL path
   basename is recorded as the original filename if present.
4. The cache key is computed from `work/input.docx` and conversion-affecting options.
5. The executor invokes docx2tex with `orig_name=input.docx`.
6. Cache save/restore uses `input` as the cached basename.
7. Packaging writes the ZIP to `<public_root>/<display_basename>.zip`.
8. The ZIP contains `<display_basename>.tex`, and debug mode also contains
   `<display_basename>.xml` / `<display_basename>.csv` if present.
9. `manifest.json` records both internal and display names.

## Compatibility

The HTTP request shape remains unchanged. Existing clients continue to upload `file`
or submit `url`. The result endpoint continues to return `application/zip`, but the
download filename now reflects the original user-facing basename instead of the
previous translated basename.
