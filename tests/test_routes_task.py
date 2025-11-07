from __future__ import annotations

import io
import os
import tempfile
from pathlib import Path

import pytest
from fastapi import FastAPI

# Require httpx for TestClient; skip if missing
pytest.importorskip("httpx")


def test_task_lifecycle_with_stubbed_background_job():
    # Prepare isolated env before importing routes (Ctx is created at import time)
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        os.environ["DATA_ROOT"] = str(td / "data")
        os.environ["WORK_ROOT"] = str(td / "work")
        os.environ["LOG_DIR"] = str(td / "logs")
        os.environ["DOCX2TEX_HOME"] = str(td / "d2t")  # not used when we provide conf

        # Import router after env setup
        from app.api import routes as r
        from fastapi.testclient import TestClient

        # Build app with router
        app = FastAPI()
        app.include_router(r.router)
        client = TestClient(app)

        # Stub background submit to avoid heavy processing
        r.ctx.jobs.submit = lambda **kwargs: None  # type: ignore[assignment]

        # Minimal conf to avoid default conf path access
        conf_xml = b"""<?xml version='1.0'?><set xmlns='http://transpect.io/xml2tex'/>"""

        # 1) Create task via file upload
        files = {
            "file": ("sample.docx", b"FAKE-DOCX", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
            "conf": ("conf.xml", conf_xml, "application/xml"),
        }
        data = {"debug": "false", "img_post_proc": "false"}
        resp = client.post("/v1/task", data=data, files=files)
        assert resp.status_code == 200
        payload = resp.json()
        task_id = payload["task_id"]
        assert task_id

        # Before completion: status should not be done; result should 409
        resp = client.get(f"/v1/task/{task_id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["state"] in {"pending", "running"}
        resp = client.get(f"/v1/task/{task_id}/result")
        assert resp.status_code == 409

        # 2) Simulate completion: mark DB state done and create expected ZIP
        js = r.ctx.jobs.get(task_id)
        # mark as done
        r.ctx.tasks.set_state(task_id, "done")
        # expected basename when no .tex exists is work-dir name
        basename = Path(js.work_dir).name
        out_zip = Path(r.ctx.cfg.public_root) / f"{basename}.zip"
        out_zip.parent.mkdir(parents=True, exist_ok=True)
        out_zip.write_bytes(b"PK\x05\x06" + b"\x00" * 18)  # minimal empty zip EOCD

        # Status reflects done
        resp = client.get(f"/v1/task/{task_id}")
        assert resp.status_code == 200
        assert resp.json()["data"]["state"] == "done"

        # Result available
        resp = client.get(f"/v1/task/{task_id}/result")
        assert resp.status_code == 200
        assert resp.headers.get("content-type") == "application/zip"

