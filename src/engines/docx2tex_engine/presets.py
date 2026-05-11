from __future__ import annotations

from pathlib import Path
from typing import Final

from .assets import resolve_conf_assets_root

CONF_DIR = resolve_conf_assets_root()

CONF_PRESETS: Final[dict[str, dict[str, str]]] = {
    "conf-book-en": {"label": "Book (English)", "path": str(CONF_DIR / "conf-book-en.xml")},
    "conf-ctexart-zh": {
        "label": "CTeX Art (中文)",
        "path": str(CONF_DIR / "conf-ctexart-zh.xml"),
    },
    "conf-ctexbook-zh": {
        "label": "CTeX Book (中文)",
        "path": str(CONF_DIR / "conf-ctexbook-zh.xml"),
    },
    "conf-elsarticle-en": {
        "label": "Elsevier Article (English)",
        "path": str(CONF_DIR / "conf-elsarticle-en.xml"),
    },
}

CUSTOM_XSL_PRESETS: Final[dict[str, dict[str, str | None]]] = {
    "none": {"label": "不注入", "path": None},
    "force-zh-cn-lang": {
        "label": "force-zh-cn-lang.xsl",
        "path": str(CONF_DIR / "force-zh-cn-lang.xsl"),
    },
}

TABLE_MODELS: Final[list[dict[str, str]]] = [
    {"id": "tabularx", "label": "tabularx"},
    {"id": "tabular", "label": "tabular"},
    {"id": "htmltabs", "label": "htmltabs"},
]

MATH_TYPE_SOURCES: Final[list[dict[str, str]]] = [
    {"id": "ole", "label": "ole"},
    {"id": "wmf", "label": "wmf"},
    {"id": "ole+wmf", "label": "ole+wmf"},
]

DEFAULTS: Final[dict[str, str | bool]] = {
    "profile_id": "docx_to_latex/docx2tex-ctexbook",
    "custom_xsl_preset": "none",
    "table_model": "tabularx",
    "math_type_source": "ole+wmf",
    "debug": False,
}


def resolve_conf_preset(preset_id: str | None) -> Path | None:
    if not preset_id:
        return None
    meta = CONF_PRESETS.get(preset_id)
    return Path(str(meta["path"])).resolve() if meta else None


def resolve_custom_xsl_preset(preset_id: str | None) -> Path | None:
    if not preset_id:
        return None
    meta = CUSTOM_XSL_PRESETS.get(preset_id)
    if not meta or meta["path"] is None:
        return None
    return Path(str(meta["path"])).resolve()
