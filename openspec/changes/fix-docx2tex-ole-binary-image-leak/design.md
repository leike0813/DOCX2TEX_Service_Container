# Design

## Repair Strategy

The fix is split into two layers:

- built-in `docx2tex` conf presets suppress `role="OLEObject"` and `.bin` `dbk:imagedata`
  before they emit `\includegraphics`
- engine-side TeX postprocessing comments any remaining `.bin` `\includegraphics` references
  and prevents those assets from entering release image bundles

This combination keeps built-in profiles clean while also protecting custom conf uploads and
restored cache results.

## Packaging Behavior

- release bundles keep compilable assets only
- OLE `.bin` references are rewritten as TeX comments with an explanatory note
- OLE `.bin` files are skipped from the release `image/` directory
- debug bundles still include raw `.docx.tmp` and debug trees, so original `.bin` assets remain
  available for diagnosis even though the final `.tex` is cleaned up

## Manifest Data

The docx2tex manifest records:

- number of OLE binary references commented out
- original TeX paths of those references
- number of `.bin` assets skipped from the release bundle
- resolved asset paths skipped during packaging
