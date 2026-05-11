from __future__ import annotations

from pathlib import Path
from urllib.parse import quote
from zipfile import ZIP_DEFLATED, ZipFile

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse

from document_conversion.application import PlatformService, PlatformTaskSubmission
from document_conversion.infrastructure.storage import write_bytes
from document_conversion.infrastructure.runtime import build_platform_context
from engines.docx2tex_engine.convert import rewrite_conf_imports_to_default
from engines.docx2tex_engine.stylemap import prepare_effective_xsls

router = APIRouter()
ctx = build_platform_context()
service = PlatformService(ctx)

_WEBUI_DIR = (
    Path(__file__).resolve().parents[1] / "webui"
)


@router.get("/")
def webui_index():
    return FileResponse(_WEBUI_DIR / "index.html")


@router.get("/webui/style.css")
def webui_style():
    return FileResponse(_WEBUI_DIR / "style.css", media_type="text/css")


@router.get("/webui/app.js")
def webui_script():
    return FileResponse(_WEBUI_DIR / "app.js", media_type="application/javascript")


@router.get("/healthz")
def healthz():
    return {"status": "ok"}


@router.get("/version")
def version():
    return {
        "service": "document-conversion-platform",
        "docx2tex_home": str(ctx.cfg.docx2tex_home),
        "platform_package": "document_conversion",
    }


@router.get("/v1/capabilities")
def get_capabilities():
    return JSONResponse(service.list_capabilities())


@router.get("/v1/profiles")
def get_profiles():
    return JSONResponse(service.list_profiles())


@router.post("/v2/tasks")
async def create_platform_task(
    file: UploadFile | None = File(default=None),
    url: str | None = Form(default=None),
    source_format: str = Form(default="docx"),
    target_format: str = Form(default="latex"),
    profile_id: str | None = Form(default=None),
    debug: bool = Form(default=False),
    img_post_proc: bool = Form(default=True),
    conf: UploadFile | None = File(default=None),
    custom_xsl: UploadFile | None = File(default=None),
    custom_xsl_preset: str | None = Form(default=None),
    custom_evolve: UploadFile | None = File(default=None),
    style_map: str | None = Form(default=None, alias="StyleMap"),
    math_type_source: str | None = Form(default=None, alias="MathTypeSource"),
    table_model: str | None = Form(default=None, alias="TableModel"),
    fontmaps_zip: UploadFile | None = File(default=None, alias="FontMapsZip"),
    image_dir: str | None = Form(default=None),
    main_tex: str | None = Form(default=None),
    reference_doc_id: str | None = Form(default=None),
    numbering_metadata_id: str | None = Form(default=None),
    lua_filter_ids: str | None = Form(default=None),
    exec_filter_ids: str | None = Form(default=None),
    top_level_division: str | None = Form(default=None),
    citeproc: bool = Form(default=False),
    csl_id: str | None = Form(default=None),
    bibliography_paths: str | None = Form(default=None),
):
    result = await service.submit_task(
        PlatformTaskSubmission(
            source_format=source_format,
            target_format=target_format,
            profile_id=profile_id,
            file=file,
            url=url,
            debug=debug,
            img_post_proc=img_post_proc,
            conf=conf,
            custom_xsl=custom_xsl,
            custom_xsl_preset=custom_xsl_preset,
            custom_evolve=custom_evolve,
            style_map=style_map,
            math_type_source=math_type_source,
            table_model=table_model,
            fontmaps_zip=fontmaps_zip,
            image_dir=image_dir,
            main_tex=main_tex,
            reference_doc_id=reference_doc_id,
            numbering_metadata_id=numbering_metadata_id,
            lua_filter_ids=lua_filter_ids,
            exec_filter_ids=exec_filter_ids,
            top_level_division=top_level_division,
            citeproc=citeproc,
            csl_id=csl_id,
            bibliography_paths=bibliography_paths,
        )
    )
    return JSONResponse(result)


@router.get("/v2/tasks/{task_id}")
def get_platform_task(task_id: str):
    task = service.get_task(task_id)
    return JSONResponse(task.__dict__)


@router.get("/v2/tasks/{task_id}/result")
def get_platform_result(task_id: str):
    task, result_path = service.result_path(task_id)
    if task.state != "done":
        raise HTTPException(status_code=409, detail=f"task state: {task.state}")
    if not result_path.exists():
        raise HTTPException(status_code=500, detail="result missing")
    return StreamingResponse(
        open(result_path, "rb"),
        media_type="application/zip",
        headers={"Content-Disposition": _content_disposition(result_path.name)},
    )


def _content_disposition(filename: str) -> str:
    ascii_fallback = "".join(
        char if 32 <= ord(char) < 127 and char not in {'"', "\\", ";"} else "_"
        for char in filename
    ).strip("_")
    if not ascii_fallback:
        ascii_fallback = "result.zip"
    return f"attachment; filename=\"{ascii_fallback}\"; filename*=UTF-8''{quote(filename)}"


@router.post("/v2/dryrun")
async def dryrun(
    conf: UploadFile | None = File(default=None),
    custom_evolve: UploadFile | None = File(default=None),
    StyleMap: str | None = Form(default=None),
):
    work = ctx.cfg.data_root / "dryrun" / "platform"
    work.mkdir(parents=True, exist_ok=True)
    conf_path = None
    if conf is not None:
        conf_path = work / "conf.xml"
        write_bytes(conf_path, await conf.read())
        try:
            rewrite_conf_imports_to_default(conf_path, ctx.cfg.docx2tex_home / "conf" / "conf.xml")
        except Exception:
            pass

    custom_evolve_path = None
    if custom_evolve is not None:
        custom_evolve_path = work / "custom-evolve-hub-driver.xsl"
        write_bytes(custom_evolve_path, await custom_evolve.read())

    effective_evolve = None
    if StyleMap and StyleMap.strip():
        confs = [
            path
            for path in [ctx.cfg.docx2tex_home / "conf" / "conf.xml", conf_path]
            if path is not None
        ]
        effective_evolve, _, _ = prepare_effective_xsls(StyleMap, confs, custom_evolve_path, work)

    mem_zip = work / "dryrun_xsls.zip"
    files_added = 0
    with ZipFile(mem_zip, "w", ZIP_DEFLATED) as zf:
        if effective_evolve and effective_evolve.exists():
            zf.write(effective_evolve, arcname=f"xsl/{effective_evolve.name}")
            files_added += 1
        manifest = work / "stylemap_manifest.json"
        if manifest.exists():
            zf.write(manifest, arcname=manifest.name)
    if files_added == 0:
        raise HTTPException(
            status_code=400,
            detail="No effective XSLs generated (check StyleMap and conf)",
        )
    return FileResponse(mem_zip, media_type="application/zip", filename="dryrun_xsls.zip")
