from __future__ import annotations

from pathlib import Path


ENGINE_ROOT = Path(__file__).resolve().parent
ASSETS_ROOT = ENGINE_ROOT / "assets"
VENDOR_ROOT = ENGINE_ROOT / "vendor"
DOCX2TEX_VENDOR_ROOT = VENDOR_ROOT / "docx2tex"
CONF_ASSETS_ROOT = ASSETS_ROOT / "conf"
XMLCATALOG_ASSETS_ROOT = ASSETS_ROOT / "xmlcatalog"
CATALOG_TEMPLATE = XMLCATALOG_ASSETS_ROOT / "catalog.xml"


def resolve_docx2tex_home() -> Path:
    return DOCX2TEX_VENDOR_ROOT.resolve()


def resolve_conf_assets_root() -> Path:
    return CONF_ASSETS_ROOT.resolve()


def resolve_catalog_template() -> Path:
    return CATALOG_TEMPLATE.resolve()


def render_catalog(template_path: Path, docx2tex_home: Path, target_path: Path) -> Path:
    rewrite_prefix = docx2tex_home.resolve().as_uri().rstrip("/") + "/"
    content = template_path.read_text(encoding="utf-8").replace("__DOCX2TEX_HOME_URI__", rewrite_prefix)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(content, encoding="utf-8")
    return target_path.resolve()
