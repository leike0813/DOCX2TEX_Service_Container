from __future__ import annotations

import io
import tempfile
from pathlib import Path

from app.core.convert import compute_cache_key, rewrite_conf_imports_to_default


def test_rewrite_conf_imports_to_default():
    with tempfile.TemporaryDirectory() as td:
        conf = Path(td) / "conf.xml"
        default_conf = Path(td) / "default" / "conf.xml"
        default_conf.parent.mkdir(parents=True, exist_ok=True)
        default_conf.write_text("<root/>", encoding="utf-8")
        conf.write_text(
            """
<?xml version='1.0'?>
<set xmlns='http://transpect.io/xml2tex'>
  <import href='conf.xml'/>
</set>
""".strip(),
            encoding="utf-8",
        )
        changed = rewrite_conf_imports_to_default(conf, default_conf)
        assert changed
        s = conf.read_text(encoding="utf-8")
        assert default_conf.resolve().as_uri() in s


def test_compute_cache_key_changes_with_inputs():
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        docx = td / "a.docx"
        conf = td / "conf.xml"
        xsl = td / "custom.xsl"
        docx.write_bytes(b"DOCX-A")
        conf.write_text("<c>A</c>", encoding="utf-8")
        xsl.write_text("<xsl/>", encoding="utf-8")

        key1 = compute_cache_key(docx, conf, xsl, None, "ole", "tabularx", None)
        # modify conf -> key changes
        conf.write_text("<c>B</c>", encoding="utf-8")
        key2 = compute_cache_key(docx, conf, xsl, None, "ole", "tabularx", None)
        assert key1 != key2

        # keep conf but add fontmaps zip -> key changes again
        import zipfile

        fm = td / "fontmaps.zip"
        with zipfile.ZipFile(fm, "w") as z:
            z.writestr("a.txt", "x")
        key3 = compute_cache_key(docx, conf, xsl, None, "ole", "tabularx", fm)
        assert key2 != key3

