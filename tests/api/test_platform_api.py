from __future__ import annotations

import importlib
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _build_client() -> tuple[object, TestClient]:
    import document_conversion.interfaces.api.router as routes

    r = importlib.reload(routes)
    app = FastAPI()
    app.include_router(r.router)
    return r, TestClient(app)


def test_capabilities_and_profiles_endpoints(isolated_platform_env: Path):
    _, client = _build_client()

    healthz = client.get("/healthz")
    assert healthz.status_code == 200
    assert healthz.json() == {"status": "ok"}

    version = client.get("/version")
    assert version.status_code == 200
    assert version.json()["service"] == "document-conversion-platform"

    capabilities = client.get("/v1/capabilities")
    assert capabilities.status_code == 200
    payload = capabilities.json()
    assert any(
        item["path_id"] == "docx_to_latex"
        and item["engine_id"] == "docx2tex"
        and item["status"] == "implemented"
        for item in payload["capabilities"]
    )
    assert any(
        item["path_id"] == "latex_to_docx"
        and item["engine_id"] == "pandoc"
        and item["status"] == "implemented"
        for item in payload["capabilities"]
    )
    assert any(item["path_id"] == "docx_to_latex" for item in payload["matrix"]["paths"])

    profiles = client.get("/v1/profiles")
    assert profiles.status_code == 200
    body = profiles.json()
    assert body["defaults"]["profile_id"] == "docx_to_latex/docx2tex-ctexbook"
    assert any(item["id"] == "docx_to_latex/docx2tex-book-en" for item in body["profiles"])
    assert any(
        item["id"] == "latex_to_docx/pandoc-auto"
        for item in body["profiles_by_path"]["latex_to_docx"]
    )
    latex_options = body["path_options"]["latex_to_docx"]
    assert any(item["id"] == "pandoc-tex-numbering" for item in latex_options["exec_filters"])
    assert any(item["id"] == "gb-t-7714-2015-numeric" for item in latex_options["csl"])
    assert "latex_to_docx/pandoc-auto" in latex_options["defaults_by_profile"]


def test_platform_task_submission_and_matrix_paths(isolated_platform_env: Path):
    r, client = _build_client()
    submitted: list[dict[str, object]] = []
    r.ctx.jobs.submit = lambda **kwargs: submitted.append(kwargs)  # type: ignore[assignment]
    scheduled: list[tuple[object, tuple[object, ...], dict[str, object]]] = []
    r.ctx.jobs.pool.submit = lambda fn, *args, **kwargs: scheduled.append((fn, args, kwargs))  # type: ignore[assignment]

    files = {
        "file": (
            "sample.docx",
            b"FAKE-DOCX",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
    }
    data = {
        "source_format": "docx",
        "target_format": "latex",
        "profile_id": "docx_to_latex/docx2tex-book-en",
        "custom_xsl_preset": "force-zh-cn-lang",
    }
    resp = client.post("/v2/tasks", data=data, files=files)
    assert resp.status_code == 200
    assert submitted
    assert submitted[0]["source_value"] == "input.docx"
    assert submitted[0]["display_basename"] == "sample"
    work_dir = Path(str(submitted[0]["conf_file"])).parent
    assert (work_dir / "input.docx").read_bytes() == b"FAKE-DOCX"
    metadata = json.loads((work_dir / "task-metadata.json").read_text(encoding="utf-8"))
    assert metadata["original_filename"] == "sample.docx"
    assert metadata["display_basename"] == "sample"
    assert metadata["internal_basename"] == "input"
    assert metadata["result_name"] == "sample.zip"
    conf_file = submitted[0]["conf_file"]
    assert conf_file is not None
    conf_text = Path(str(conf_file)).read_text(encoding="utf-8")
    assert str((r.ctx.cfg.docx2tex_home / "conf" / "conf.xml").resolve().as_uri()) in conf_text
    assert "OLEObject" in conf_text
    assert "\\\\.bin$" in conf_text

    future = client.post(
        "/v2/tasks",
        data={
            "source_format": "latex",
            "target_format": "markdown",
            "profile_id": "latex_to_markdown/pandoc-default",
        },
        files={"file": ("workspace.zip", b"PK\x03\x04", "application/zip")},
    )
    assert future.status_code == 501

    reverse = client.post(
        "/v2/tasks",
        data={
            "source_format": "latex",
            "target_format": "docx",
            "profile_id": "latex_to_docx/pandoc-auto",
        },
        files={"file": ("workspace.zip", b"PK\x03\x04", "application/zip")},
    )
    assert reverse.status_code == 200
    assert scheduled

    reverse_with_options = client.post(
        "/v2/tasks",
        data={
            "source_format": "latex",
            "target_format": "docx",
            "profile_id": "latex_to_docx/pandoc-ctexbook",
            "main_tex": "main.tex",
            "reference_doc_id": "ctexbook",
            "numbering_metadata_id": "zh-book",
            "lua_filter_ids": json.dumps(["caption-colon-to-space"]),
            "exec_filter_ids": json.dumps(["pandoc-tex-numbering"]),
            "top_level_division": "chapter",
            "citeproc": "true",
            "csl_id": "gb-t-7714-2015-numeric",
            "bibliography_paths": json.dumps(["refs.bib"]),
        },
        files={"file": ("workspace.zip", b"PK\x03\x04", "application/zip")},
    )
    assert reverse_with_options.status_code == 200


def test_docx2tex_non_ascii_filename_uses_internal_input_name(isolated_platform_env: Path):
    r, client = _build_client()
    submitted: list[dict[str, object]] = []
    r.ctx.jobs.submit = lambda **kwargs: submitted.append(kwargs)  # type: ignore[assignment]

    response = client.post(
        "/v2/tasks",
        data={
            "source_format": "docx",
            "target_format": "latex",
            "profile_id": "docx_to_latex/docx2tex-book-en",
        },
        files={
            "file": (
                "安全报告.docx",
                b"SAME-DOCX",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 200
    assert submitted
    assert submitted[0]["source_value"] == "input.docx"
    assert submitted[0]["original_filename"] == "安全报告.docx"
    assert submitted[0]["display_basename"] == "安全报告"
    work_dir = Path(str(submitted[0]["conf_file"])).parent
    assert (work_dir / "input.docx").read_bytes() == b"SAME-DOCX"
    metadata = json.loads((work_dir / "task-metadata.json").read_text(encoding="utf-8"))
    assert metadata["result_name"] == "安全报告.zip"


def test_docx2tex_stylemap_submission_builds_effective_artifacts(isolated_platform_env: Path):
    r, client = _build_client()
    submitted: list[dict[str, object]] = []
    r.ctx.jobs.submit = lambda **kwargs: submitted.append(kwargs)  # type: ignore[assignment]

    response = client.post(
        "/v2/tasks",
        data={
            "source_format": "docx",
            "target_format": "latex",
            "profile_id": "docx_to_latex/docx2tex-ctexbook",
            "StyleMap": '{"Title":["Main Title"],"Heading1":["Level 1 Heading"]}',
        },
        files={
            "file": (
                "sample.docx",
                b"FAKE-DOCX",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )

    assert response.status_code == 200
    assert submitted
    evolve_path = submitted[0]["custom_evolve"]
    assert evolve_path is not None
    evolve_file = Path(str(evolve_path))
    assert evolve_file.exists()
    assert (evolve_file.parent / "stylemap_manifest.json").exists()


def test_removed_v1_task_endpoints_return_not_found(isolated_platform_env: Path):
    _, client = _build_client()

    assert client.post("/v1/task").status_code == 404
    assert client.get("/v1/task/example").status_code == 404
    assert client.get("/v1/task/example/result").status_code == 404
    assert client.get("/v1/ui/presets").status_code == 404
    assert client.post("/v1/dryrun").status_code == 404


def test_v2_dryrun_builds_effective_xsl(isolated_platform_env: Path):
    _, client = _build_client()
    conf_xml = (
        "<?xml version='1.0'?><set xmlns='http://transpect.io/xml2tex'>"
        "<import href='conf.xml'/></set>"
    ).encode("utf-8")
    files = {"conf": ("conf.xml", conf_xml, "application/xml")}
    data = {"StyleMap": '{"Title":"主标题"}'}

    response = client.post("/v2/dryrun", data=data, files=files)
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"


def test_webui_root_page_renders(isolated_platform_env: Path):
    _, client = _build_client()

    response = client.get("/")
    assert response.status_code == 200
    assert "在浏览器里完成文档格式互转" in response.text
    assert "转换路径" in response.text
    assert "Pandoc 路线" in response.text
    assert "样式映射注入" in response.text
    assert "top-level-division" in response.text
    assert "/webui/app.js" in response.text
