from __future__ import annotations

from document_conversion.domain import ConversionProfile

DOCX2TEX_PATH_ID = "docx_to_latex"

DOCX2TEX_PROFILES: list[ConversionProfile] = [
    ConversionProfile(
        id="docx_to_latex/docx2tex-book-en",
        label="Book (English)",
        path_id=DOCX2TEX_PATH_ID,
        engine_id="docx2tex",
        description="Use assets/conf/conf-book-en.xml",
        engine_options={"conf_preset_id": "conf-book-en"},
    ),
    ConversionProfile(
        id="docx_to_latex/docx2tex-ctexart",
        label="CTeX Art (中文)",
        path_id=DOCX2TEX_PATH_ID,
        engine_id="docx2tex",
        description="Use assets/conf/conf-ctexart-zh.xml",
        engine_options={"conf_preset_id": "conf-ctexart-zh"},
    ),
    ConversionProfile(
        id="docx_to_latex/docx2tex-ctexbook",
        label="CTeX Book (中文)",
        path_id=DOCX2TEX_PATH_ID,
        engine_id="docx2tex",
        description="Use assets/conf/conf-ctexbook-zh.xml",
        engine_options={"conf_preset_id": "conf-ctexbook-zh"},
    ),
    ConversionProfile(
        id="docx_to_latex/docx2tex-elsarticle",
        label="Elsevier Article (English)",
        path_id=DOCX2TEX_PATH_ID,
        engine_id="docx2tex",
        description="Use assets/conf/conf-elsarticle-en.xml",
        engine_options={"conf_preset_id": "conf-elsarticle-en"},
    ),
]
