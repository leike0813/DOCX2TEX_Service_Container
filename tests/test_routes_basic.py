from __future__ import annotations

import importlib
import os
import tempfile

import pytest
from fastapi import FastAPI

# Skip if httpx not installed (required by TestClient)
pytest.importorskip("httpx")


def test_healthz_and_version():
    with tempfile.TemporaryDirectory() as td:
        os.environ["DATA_ROOT"] = td
        os.environ["WORK_ROOT"] = td
        os.environ["LOG_DIR"] = td

        import app.api.routes as routes
        r = importlib.reload(routes)

        from fastapi.testclient import TestClient

        app = FastAPI()
        app.include_router(r.router)
        client = TestClient(app)

        resp = client.get("/healthz")
        assert resp.status_code == 200
        assert resp.json().get("status") == "ok"

        resp = client.get("/version")
        assert resp.status_code == 200
        body = resp.json()
        assert body.get("service") == "docx2tex-service"

