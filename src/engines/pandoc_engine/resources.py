from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ENGINE_ROOT = Path(__file__).resolve().parent
ASSETS_ROOT = ENGINE_ROOT / "assets"
METADATA_ROOT = ASSETS_ROOT / "metadata"
CSL_ROOT = ASSETS_ROOT / "csl"
FILTER_ROOT = ASSETS_ROOT / "filters"


@dataclass(frozen=True)
class BuiltinFileResource:
    id: str
    label: str
    path: Path | None = None
    binary_name: str | None = None


REFERENCE_DOCS: dict[str, BuiltinFileResource] = {
    "article-default": BuiltinFileResource("article-default", "Article Default"),
    "ctexart": BuiltinFileResource("ctexart", "CTeX Art"),
    "ctexbook": BuiltinFileResource("ctexbook", "CTeX Book"),
    "elsarticle": BuiltinFileResource("elsarticle", "Elsevier Article"),
}

NUMBERING_METADATA: dict[str, BuiltinFileResource] = {
    "zh-default": BuiltinFileResource(
        "zh-default",
        "中文默认编号",
        METADATA_ROOT / "custom-meta.yaml",
    ),
    "zh-report": BuiltinFileResource(
        "zh-report",
        "中文报告编号",
        METADATA_ROOT / "custom-meta-report.yaml",
    ),
    "zh-book": BuiltinFileResource(
        "zh-book",
        "中文书籍编号",
        METADATA_ROOT / "meta_zh.yaml",
    ),
}

CSL_FILES: dict[str, BuiltinFileResource] = {
    "gb-t-7714-2015-numeric": BuiltinFileResource(
        "gb-t-7714-2015-numeric",
        "GB/T 7714-2015 Numeric",
        CSL_ROOT / "gb-t-7714-2015-numeric.csl",
    ),
}

LUA_FILTERS: dict[str, BuiltinFileResource] = {
    "caption-colon-to-space": BuiltinFileResource(
        "caption-colon-to-space",
        "Caption Colon To Space",
        FILTER_ROOT / "caption_colon_to_space.lua",
    ),
    "math-cleanup": BuiltinFileResource(
        "math-cleanup",
        "Math Cleanup",
        FILTER_ROOT / "math_cleanup.lua",
    ),
    "org-helper": BuiltinFileResource(
        "org-helper",
        "Org Helper",
        FILTER_ROOT / "org_helper.lua",
    ),
}

EXEC_FILTERS: dict[str, BuiltinFileResource] = {
    "pandoc-tex-numbering": BuiltinFileResource(
        "pandoc-tex-numbering",
        "pandoc-tex-numbering",
        binary_name="pandoc-tex-numbering",
    )
}

TOP_LEVEL_DIVISIONS = [
    {"id": "section", "label": "section"},
    {"id": "chapter", "label": "chapter"},
    {"id": "part", "label": "part"},
]

LATEX_TO_DOCX_DEFAULTS: dict[str, dict[str, object]] = {
    "latex_to_docx/pandoc-auto": {
        "reference_doc_id": "article-default",
        "numbering_metadata_id": "zh-default",
        "lua_filter_ids": ["caption-colon-to-space"],
        "exec_filter_ids": ["pandoc-tex-numbering"],
        "top_level_division": "section",
        "citeproc": False,
        "csl_id": "",
    },
    "latex_to_docx/pandoc-ctexart": {
        "reference_doc_id": "ctexart",
        "numbering_metadata_id": "zh-default",
        "lua_filter_ids": ["caption-colon-to-space"],
        "exec_filter_ids": ["pandoc-tex-numbering"],
        "top_level_division": "section",
        "citeproc": False,
        "csl_id": "",
    },
    "latex_to_docx/pandoc-ctexbook": {
        "reference_doc_id": "ctexbook",
        "numbering_metadata_id": "zh-book",
        "lua_filter_ids": ["caption-colon-to-space"],
        "exec_filter_ids": ["pandoc-tex-numbering"],
        "top_level_division": "chapter",
        "citeproc": False,
        "csl_id": "",
    },
    "latex_to_docx/pandoc-elsarticle": {
        "reference_doc_id": "elsarticle",
        "numbering_metadata_id": "zh-report",
        "lua_filter_ids": ["caption-colon-to-space", "org-helper"],
        "exec_filter_ids": ["pandoc-tex-numbering"],
        "top_level_division": "section",
        "citeproc": False,
        "csl_id": "",
    },
}


def latex_to_docx_option_payload() -> dict[str, object]:
    return {
        "reference_docs": _payload_list(REFERENCE_DOCS),
        "numbering_metadata": _payload_list(NUMBERING_METADATA),
        "lua_filters": _payload_list(LUA_FILTERS),
        "exec_filters": _payload_list(EXEC_FILTERS),
        "csl": _payload_list(CSL_FILES),
        "top_level_division": TOP_LEVEL_DIVISIONS,
        "defaults_by_profile": LATEX_TO_DOCX_DEFAULTS,
    }


def reference_doc_path(resource_id: str, runtime_root: Path) -> Path:
    resource = REFERENCE_DOCS.get(resource_id)
    if resource is None:
        raise KeyError(resource_id)
    out_dir = runtime_root / "pandoc_engine" / "reference-docs"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"{resource.id}.docx"
    if not target.exists():
        _write_reference_doc(resource.id, target)
    return target


def metadata_path(resource_id: str) -> Path:
    return _require_file(NUMBERING_METADATA, resource_id)


def csl_path(resource_id: str) -> Path:
    return _require_file(CSL_FILES, resource_id)


def lua_filter_path(resource_id: str) -> Path:
    return _require_file(LUA_FILTERS, resource_id)


def exec_filter_binary(resource_id: str) -> str:
    resource = EXEC_FILTERS.get(resource_id)
    if resource is None or not resource.binary_name:
        raise KeyError(resource_id)
    return resource.binary_name


def available_exec_filter(resource_id: str) -> bool:
    return shutil.which(exec_filter_binary(resource_id)) is not None


def auto_reference_doc_id(template_name: str) -> str:
    return {
        "ctexart": "ctexart",
        "ctexbook": "ctexbook",
        "elsarticle": "elsarticle",
    }.get(template_name, "article-default")


def default_latex_to_docx_options(profile_id: str) -> dict[str, object]:
    return dict(LATEX_TO_DOCX_DEFAULTS.get(profile_id, LATEX_TO_DOCX_DEFAULTS["latex_to_docx/pandoc-auto"]))


def _payload_list(items: dict[str, BuiltinFileResource]) -> list[dict[str, str]]:
    return [{"id": item.id, "label": item.label} for item in items.values()]


def _require_file(items: dict[str, BuiltinFileResource], resource_id: str) -> Path:
    resource = items.get(resource_id)
    if resource is None or resource.path is None or not resource.path.exists():
        raise KeyError(resource_id)
    return resource.path.resolve()


def _write_reference_doc(resource_id: str, target: Path) -> None:
    styles = _reference_styles(resource_id)
    with ZipFile(target, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>""",
        )
        archive.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>""",
        )
        archive.writestr(
            "word/document.xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>Reference template</w:t></w:r></w:p>
    <w:sectPr/>
  </w:body>
</w:document>""",
        )
        archive.writestr("word/styles.xml", styles)
        archive.writestr(
            "docProps/core.xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
 xmlns:dc="http://purl.org/dc/elements/1.1/"
 xmlns:dcterms="http://purl.org/dc/terms/"
 xmlns:dcmitype="http://purl.org/dc/dcmitype/"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>document-conversion reference</dc:title>
</cp:coreProperties>""",
        )
        archive.writestr(
            "docProps/app.xml",
            """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
 xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>document-conversion</Application>
</Properties>""",
        )


def _reference_styles(resource_id: str) -> str:
    east_asia = "宋体" if resource_id in {"ctexart", "ctexbook"} else "Times New Roman"
    ascii_font = "Times New Roman"
    heading_size = "36" if resource_id == "ctexbook" else "32"
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:docDefaults>
    <w:rPrDefault>
      <w:rPr>
        <w:rFonts w:ascii="{ascii_font}" w:hAnsi="{ascii_font}" w:eastAsia="{east_asia}"/>
        <w:sz w:val="24"/>
      </w:rPr>
    </w:rPrDefault>
  </w:docDefaults>
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:qFormat/>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:rPr>
      <w:rFonts w:ascii="{ascii_font}" w:hAnsi="{ascii_font}" w:eastAsia="{east_asia}"/>
      <w:b/>
      <w:sz w:val="{heading_size}"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading2">
    <w:name w:val="heading 2"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:rPr>
      <w:rFonts w:ascii="{ascii_font}" w:hAnsi="{ascii_font}" w:eastAsia="{east_asia}"/>
      <w:b/>
      <w:sz w:val="28"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Caption">
    <w:name w:val="Caption"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
  </w:style>
</w:styles>"""
