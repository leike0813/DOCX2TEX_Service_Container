# add-pandoc-vector-image-to-emf-pipeline

## Why

The current `latex -> docx@pandoc` path does not explicitly preprocess vector image assets.
It mostly depends on Pandoc's raw resource handling, which is not strong enough for a formal
conversion path.

## What Changes

- add an explicit `\includegraphics` asset preprocessor for `svg`, `pdf`, and `eps`
- convert vector images to `emf` with Inkscape
- allow `pdf/eps -> png` fallback at `300 DPI`, but keep `svg` strict to `emf`
- include image conversion summaries in manifests and debug bundles
