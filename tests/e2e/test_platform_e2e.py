from __future__ import annotations

import importlib
import io
import os
import shutil
import time
from zipfile import ZipFile

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.mark.e2e
@pytest.mark.skipif(
    os.environ.get("DOCX2TEX_E2E") != "1" or shutil.which("pandoc-tex-numbering") is None,
    reason="set DOCX2TEX_E2E=1 and install pandoc-tex-numbering to enable slow tests",
)
def test_real_latex_to_docx_pandoc_roundtrip(isolated_platform_env):
    import document_conversion.interfaces.api.router as routes

    router_module = importlib.reload(routes)
    app = FastAPI()
    app.include_router(router_module.router)
    client = TestClient(app)

    payload = io.BytesIO()
    with ZipFile(payload, "w") as archive:
        archive.writestr(
            "main.tex",
            "\\documentclass{article}\n\\begin{document}\nHello pandoc.\n\\end{document}\n",
        )
    payload.seek(0)

    response = client.post(
        "/v2/tasks",
        data={
            "source_format": "latex",
            "target_format": "docx",
            "profile_id": "latex_to_docx/pandoc-auto",
            "citeproc": "false",
        },
        files={"file": ("workspace.zip", payload.read(), "application/zip")},
    )
    assert response.status_code == 200
    task_id = response.json()["task_id"]

    deadline = time.time() + 30
    while time.time() < deadline:
        task = client.get(f"/v2/tasks/{task_id}")
        assert task.status_code == 200
        state = task.json()["state"]
        if state == "done":
            break
        if state == "failed":
            raise AssertionError(task.json()["err_msg"])
        time.sleep(1.0)
    else:
        raise AssertionError("pandoc e2e task did not finish in time")

    result = client.get(f"/v2/tasks/{task_id}/result")
    assert result.status_code == 200
    with ZipFile(io.BytesIO(result.content), "r") as archive:
        names = set(archive.namelist())
    assert "result.docx" in names


@pytest.mark.e2e
@pytest.mark.skipif(
    os.environ.get("DOCX2TEX_E2E") != "1"
    or shutil.which("pandoc-tex-numbering") is None
    or shutil.which("inkscape") is None,
    reason="set DOCX2TEX_E2E=1 and install pandoc-tex-numbering and inkscape to enable slow tests",
)
def test_real_latex_to_docx_with_svg_preprocessing(isolated_platform_env):
    import document_conversion.interfaces.api.router as routes

    router_module = importlib.reload(routes)
    app = FastAPI()
    app.include_router(router_module.router)
    client = TestClient(app)

    payload = io.BytesIO()
    with ZipFile(payload, "w") as archive:
        archive.writestr(
            "main.tex",
            "\\documentclass{article}\n"
            "\\usepackage{graphicx}\n"
            "\\begin{document}\n"
            "\\includegraphics{plot.svg}\n"
            "\\end{document}\n",
        )
        archive.writestr(
            "plot.svg",
            "<svg xmlns='http://www.w3.org/2000/svg' width='100' height='40'>"
            "<rect x='0' y='0' width='100' height='40' fill='#ffffff' stroke='#000000'/>"
            "<text x='10' y='25' font-size='14'>plot</text>"
            "</svg>",
        )
    payload.seek(0)

    response = client.post(
        "/v2/tasks",
        data={
            "source_format": "latex",
            "target_format": "docx",
            "profile_id": "latex_to_docx/pandoc-auto",
            "debug": "true",
            "citeproc": "false",
        },
        files={"file": ("workspace.zip", payload.read(), "application/zip")},
    )
    assert response.status_code == 200
    task_id = response.json()["task_id"]

    deadline = time.time() + 30
    while time.time() < deadline:
        task = client.get(f"/v2/tasks/{task_id}")
        assert task.status_code == 200
        state = task.json()["state"]
        if state == "done":
            break
        if state == "failed":
            raise AssertionError(task.json()["err_msg"])
        time.sleep(1.0)
    else:
        raise AssertionError("pandoc svg e2e task did not finish in time")

    result = client.get(f"/v2/tasks/{task_id}/result")
    assert result.status_code == 200
    with ZipFile(io.BytesIO(result.content), "r") as archive:
        names = set(archive.namelist())
        manifest = archive.read("manifest.json").decode("utf-8")
    assert "result.docx" in names
    assert any(name.startswith("generated-images/") and name.endswith(".emf") for name in names)
    assert "\"image_conversions\"" in manifest
