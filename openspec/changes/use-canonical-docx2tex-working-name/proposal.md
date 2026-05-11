# use-canonical-docx2tex-working-name

## Summary

Replace the docx2tex route's translated filename strategy with a canonical internal
working filename. The service will preserve the user's original filename as metadata,
run docx2tex against a stable ASCII name, and publish result bundles using the
recorded user-facing basename.

## Motivation

The current filename sanitizer attempts to translate or transliterate Chinese and
other non-ASCII filenames into English-like ASCII names before invoking docx2tex.
That adds language-library complexity to solve a problem that can be isolated at
the service boundary. docx2tex only needs a stable safe input name; users need the
final downloaded bundle to retain the original document identity.

## Change

- Store uploaded or downloaded docx2tex inputs as `input.docx` in the task work
  directory.
- Record the original filename, user-facing basename, and internal basename in task
  metadata.
- Run docx2tex, cache restore/save, debug output, and intermediate artifacts with
  the internal basename `input`.
- Publish result ZIPs as `<display_basename>.zip`.
- Write user-facing main artifacts in the ZIP as `<display_basename>.tex` and, in
  debug mode, `<display_basename>.xml` / `<display_basename>.csv`.
- Keep internal debug directories as `input.debug` and `input.docx.tmp`, while
  recording the mapping in `manifest.json`.
- Retire the complex Chinese-to-English filename transliteration path for main
  DOCX inputs.

## Non-Goals

- Do not change the public task submission API.
- Do not change the pandoc ZIP workspace naming strategy.
- Do not introduce a user-visible filename override field.
- Do not change image directory naming beyond existing safety checks.
