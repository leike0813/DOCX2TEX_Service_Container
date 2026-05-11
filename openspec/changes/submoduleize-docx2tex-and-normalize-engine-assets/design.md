# Design

## Target Layout

The repository uses three distinct classes of engine material:

1. `vendor/`
   Third-party source trees that are not authored in this repository and should be
   versioned independently. For `docx2tex`, this is a git submodule.

2. `assets/`
   Runtime-owned files maintained by this repository and required for execution. These
   include profile configs, XML catalog templates, Lua filters, and YAML templates.

3. `resources/`
   Samples, prototypes, and research materials that are useful for tests, examples, or
   documentation but are not the runtime source of truth.

The normalized engine layout is:

```text
src/engines/<engine>/
  converter.py
  profiles.py
  assets/
  vendor/        # optional
resources/<engine>/
```

## docx2tex Normalization

`docx2tex` is an upstream dependency of the `docx2tex` engine, not a root-level project
artifact. The canonical vendor location becomes:

`src/engines/docx2tex_engine/vendor/docx2tex`

Repository-owned configs and XML catalog material move under:

- `src/engines/docx2tex_engine/assets/conf/`
- `src/engines/docx2tex_engine/assets/xmlcatalog/`

The platform resolves:

- `DOCX2TEX_HOME` from the vendor submodule path by default
- `XML_CATALOG_FILES` from an engine-owned XML catalog template that is rewritten to the
  effective vendor path at runtime

## Compatibility Shell

`src/docx2tex_service` remains in the tree only to preserve import compatibility for
entrypoints. It must not own domain, application, or infrastructure implementations.
Only these public forwarding modules remain:

- `src/docx2tex_service/__init__.py`
- `src/docx2tex_service/interfaces/cli.py`
- `src/docx2tex_service/interfaces/api/app.py`
- `src/docx2tex_service/interfaces/api/router.py`

## Runtime Resolution

The platform runtime resolves engine-local paths through explicit helpers rather than by
searching the repository root. This keeps local development, tests, and container builds
aligned around the same package-relative contract.

For `docx2tex`, the resolver exposes:

- engine root
- assets root
- vendor root
- default conf asset directory
- vendor `docx2tex` home
- effective XML catalog path

## Build And Deployment

Docker and local deploy scripts stop assuming root-level `docx2tex/`, `catalog/`, or
`conf/` directories. The image now copies the checked-in submodule and engine assets from
`src/engines/docx2tex_engine/` and launches the platform directly from
`document_conversion`.

## Documentation

`docs/architecture.md` becomes the authoritative architecture document. It must describe:

- the platform package versus engine packages
- compatibility shell boundaries
- asset versus vendor versus resources semantics
- submodule policy
- runtime path resolution rules
