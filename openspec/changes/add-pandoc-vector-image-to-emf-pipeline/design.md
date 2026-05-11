# Design

## Preprocessor Placement

Vector image handling is added to the Pandoc LaTeX preprocessor chain. This keeps the feature
inside the existing `latex -> docx@pandoc` orchestration path and allows the engine to rewrite
`\includegraphics{...}` references before Pandoc reads the generated TeX.

## Conversion Rules

- `svg` -> `emf`
- `pdf` -> `emf`, then fallback `png@300dpi`
- `eps` -> `emf`, then fallback `png@300dpi`

When conversion fails, the preprocessor keeps the original asset by rewriting to a resolved
filesystem path instead of aborting the task.

## Runtime Data Flow

The preprocessor receives:

- source TeX directory
- extracted workspace root
- Pandoc work directory generated-images output path

It returns:

- rewritten TeX
- successful image conversions
- final conversion failures
- fallback records
- generated image file list for debug packaging
