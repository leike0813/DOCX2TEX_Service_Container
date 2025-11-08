from __future__ import annotations

import json
import tempfile
from pathlib import Path

from app.core.stylemap import prepare_effective_xsls


def test_stylemap_prepares_effective_evolve_xsl():
    # This test runs outside container and doesn't invoke Calabash.
    # It verifies that StyleMap + xml2tex conf can produce an effective evolve XSL.
    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        # Use one of the project-provided xml2tex configurations
        conf = Path("conf") / "conf-ctexbook-zh.xml"
        assert conf.exists(), f"missing conf: {conf}"

        style = {"Title": "主标题", "Heading1": "I级标题"}
        ee, style_map, role_cmds = prepare_effective_xsls(
            json.dumps(style, ensure_ascii=False),
            [conf],
            user_custom_evolve=None,
            user_custom_xsl=None,
            work_dir=work,
        )

        # Should produce an evolve-driver file with our snippets merged/created
        assert ee is not None and ee.exists(), "effective evolve XSL not created"
        text = ee.read_text(encoding="utf-8")
        # Sanity: contains our variables or templates and imported base driver
        assert "evolve-hub-driver.xsl" in text or "docx2tex-preprocess" in text
        # Ensure role mapping keys recognized (intersection may vary by conf)
        assert any(k in style_map for k in ("Title", "Heading1"))
