# fix-docx2tex-ole-binary-image-leak

## Why

The current `docx -> latex@docx2tex` path can leak `oleObject*.bin` references into the final
TeX output when Word embeds OLE objects such as Visio drawings. This yields uncompilable
`\includegraphics{...bin}` commands and also causes those binary payloads to be packed into the
release bundle image directory.

## What Changes

- suppress built-in profile generation of OLE `.bin` image references
- add a postprocess guard that comments uncompilable OLE binary `\includegraphics` references
- exclude OLE `.bin` assets from release image bundles while preserving them in debug artifacts
- record OLE cleanup actions in `manifest.json`
