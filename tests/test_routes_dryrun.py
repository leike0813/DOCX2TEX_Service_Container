from __future__ import annotations

import importlib
import io
import json
import os
import tempfile
from pathlib import Path

from fastapi import FastAPI
from zipfile import ZipFile
import pytest

# Skip if httpx (required by TestClient) is not installed
pytest.importorskip("httpx")


def test_dryrun_builds_effective_xsl():
    with tempfile.TemporaryDirectory() as td_str:
        td = Path(td_str)
        os.environ["DATA_ROOT"] = str(td / "data")
        os.environ["WORK_ROOT"] = str(td / "work")
        os.environ["LOG_DIR"] = str(td / "logs")
        repo_docx2tex = Path.cwd() / "docx2tex"
        os.environ["DOCX2TEX_HOME"] = str(repo_docx2tex if repo_docx2tex.exists() else (td / "d2t"))

        import app.api.routes as routes
        r = importlib.reload(routes)

        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(r.router)
        client = TestClient(app)

        conf_xml = """
<?xml version='1.0'?>
<set xmlns='http://transpect.io/xml2tex'>
  <import href='conf.xml'/>
</set>
""".strip().encode("utf-8")
        stylemap = json.dumps({"Title": "主标题", "Heading1": "I级标题"})

        files = {"conf": ("conf.xml", conf_xml, "application/xml")}
        data = {"StyleMap": stylemap}
        resp = client.post("/v1/dryrun", data=data, files=files)
        assert resp.status_code == 200

        zf = ZipFile(io.BytesIO(resp.content))
        names = zf.namelist()
        assert any(n.startswith("xsl/") for n in names)
        # optional manifest
        # not mandatory in dryrun, but if present should be a json file
        # no strict assertion here to keep test resilient to config changes
