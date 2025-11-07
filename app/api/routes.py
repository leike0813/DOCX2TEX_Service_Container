from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from app.core.config import Config, get_config
from app.core.db import Database
from app.core.cache import CacheStore, LockManager
from app.core.tasks import TaskStore
from app.core.storage import write_bytes, safe_name
from app.core.proc import download_to
from app.core.convert import rewrite_conf_imports_to_default, compute_cache_key
from app.core.stylemap import prepare_effective_xsls
from app.services.job_manager import JobManager


router = APIRouter()


class Ctx:
    def __init__(self):
        self.cfg: Config = get_config()
        self.db = Database(self.cfg.db_path)
        self.db.init_schema()
        self.cache = CacheStore(self.db, self.cfg.data_root)
        self.locks = LockManager(self.db)
        self.tasks = TaskStore(self.db)
        self.jobs = JobManager(self.cfg, self.tasks, self.cache, self.locks, workers=2)


ctx = Ctx()

@router.get("/healthz")
def healthz():
    return {"status": "ok"}

@router.get("/version")
def version():
    return {
        "service": "docx2tex-service",
        "docx2tex_home": str(ctx.cfg.docx2tex_home),
    }


@router.post("/v1/task")
async def create_task(
    file: UploadFile | None = File(default=None),
    url: str | None = Form(default=None),
    debug: bool = Form(default=False),
    img_post_proc: bool = Form(default=True),
    conf: UploadFile | None = File(default=None),
    custom_xsl: UploadFile | None = File(default=None),
    custom_evolve: UploadFile | None = File(default=None),
    StyleMap: str | None = Form(default=None),
    MathTypeSource: str | None = Form(default=None),
    TableModel: str | None = Form(default=None),
    FontMapsZip: UploadFile | None = File(default=None),
):
    if (file is None and not url) or (file is not None and url):
        raise HTTPException(status_code=400, detail="Provide exactly one of file or url")

    js = ctx.jobs.create(debug=debug, img_post_proc=img_post_proc)
    work = Path(js.work_dir)

    # Prepare input
    if file is not None:
        name = safe_name(file.filename or "document.docx")
        if not name.lower().endswith(".docx"):
            name = f"{name}.docx"
        input_docx = work / name
        await write_upload_stream(file, input_docx, ctx.cfg.max_upload_bytes)
    else:
        name = _safe_filename_from_url(url or "")
        input_docx = work / name
        download_to(input_docx, url or "")

    # Optional inputs
    conf_path: Optional[Path] = None
    if conf is not None:
        conf_path = work / "conf.xml"
        write_bytes(conf_path, await conf.read())
        try:
            rewrite_conf_imports_to_default(conf_path, ctx.cfg.docx2tex_home / "conf" / "conf.xml")
        except Exception:
            pass
    xsl_path: Optional[Path] = None
    if custom_xsl is not None:
        xsl_path = work / "custom.xsl"
        write_bytes(xsl_path, await custom_xsl.read())
    evolve_path: Optional[Path] = None
    if custom_evolve is not None:
        evolve_path = work / "custom-evolve-hub-driver.xsl"
        write_bytes(evolve_path, await custom_evolve.read())
    fontmaps_zip_path: Optional[Path] = None
    if FontMapsZip is not None:
        fontmaps_zip_path = work / "fontmaps.zip"
        write_bytes(fontmaps_zip_path, await FontMapsZip.read())

    # Prepare effective XSLs from StyleMap (if any)
    try:
        if StyleMap and StyleMap.strip():
            confs = [p for p in [conf_path, ctx.cfg.docx2tex_home / "conf" / "conf.xml"] if p is not None]
            effective_evolve, effective_xsl, style_map, role_cmds = prepare_effective_xsls(StyleMap, confs, evolve_path, xsl_path, work)
            # Only evolve-driver injection is used for StyleMap (no output-layer custom-xsl injection)
            if effective_evolve:
                evolve_path = effective_evolve
            # effective_xsl is intentionally ignored
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"StyleMap processing failed: {e}")

    # Compute cache key (same semantics)
    cache_key = compute_cache_key(
        input_docx,
        (conf_path or ctx.cfg.docx2tex_home / "conf" / "conf.xml"),
        xsl_path,
        evolve_path,
        (MathTypeSource or None),
        (TableModel or None),
        (fontmaps_zip_path or None),
    )
    cache_status = "MISS"
    row = ctx.cache.get(cache_key)
    if row and int(row.get("available", 0)) == 1:
        cache_status = "HIT"
    elif row and int(row.get("available", 0)) == 0:
        cache_status = "BUILDING"

    # Submit background job
    ctx.jobs.submit(
        task_id=js.task_id,
        source_kind=("file" if file is not None else "url"),
        source_value=(input_docx.name if file is not None else name),
        debug=debug,
        img_post_proc=img_post_proc,
        conf_file=conf_path,
        custom_xsl=xsl_path,
        custom_evolve=evolve_path,
        mtef_source=(MathTypeSource or None),
        table_model=(TableModel or None),
        fontmaps_dir=None,
        fontmaps_zip=fontmaps_zip_path,
        job_cache_key=cache_key,
    )

    return JSONResponse({"task_id": js.task_id, "cache_key": cache_key, "cache_status": cache_status})


@router.get("/v1/task/{task_id}")
def get_status(task_id: str):
    try:
        js = ctx.jobs.get(task_id)
        data = {
            "task_id": js.task_id,
            "state": js.state,
            "err_msg": js.err_msg,
            "start_time": js.start_time,
            "end_time": js.end_time,
        }
        return JSONResponse({"code": 0, "data": data, "msg": "ok"})
    except KeyError:
        raise HTTPException(status_code=404, detail="task not found")


@router.get("/v1/task/{task_id}/result")
def get_result(task_id: str):
    try:
        js = ctx.jobs.get(task_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="task not found")
    if js.state != "done":
        raise HTTPException(status_code=409, detail=f"task state: {js.state}")
    work = Path(js.work_dir)
    tex_files = list(work.glob("*.tex"))
    basename = tex_files[0].stem if tex_files else Path(work).name
    zf = ctx.cfg.public_root / f"{basename}.zip"
    if not zf.exists():
        raise HTTPException(status_code=500, detail="result missing")
    return StreamingResponse(open(zf, "rb"), media_type="application/zip", headers={"Content-Disposition": f"attachment; filename={basename}.zip"})


@router.post("/v1/dryrun")
async def dryrun(
    conf: UploadFile | None = File(default=None),
    custom_xsl: UploadFile | None = File(default=None),
    custom_evolve: UploadFile | None = File(default=None),
    StyleMap: str | None = Form(default=None),
):
    work = ctx.cfg.data_root / "dryrun" / str(uuid.uuid4())
    work.mkdir(parents=True, exist_ok=True)
    conf_path: Optional[Path] = None
    if conf is not None:
        conf_path = work / "conf.xml"
        write_bytes(conf_path, await conf.read())
        try:
            rewrite_conf_imports_to_default(conf_path, ctx.cfg.docx2tex_home / "conf" / "conf.xml")
        except Exception:
            pass
    xsl_path: Optional[Path] = None
    if custom_xsl is not None:
        xsl_path = work / "custom.xsl"
        write_bytes(xsl_path, await custom_xsl.read())
    evolve_path: Optional[Path] = None
    if custom_evolve is not None:
        evolve_path = work / "custom-evolve-hub-driver.xsl"
        write_bytes(evolve_path, await custom_evolve.read())

    try:
        confs = [p for p in [conf_path, ctx.cfg.docx2tex_home / "conf" / "conf.xml"] if p is not None]
        effective_evolve, effective_xsl, style_map, role_cmds = prepare_effective_xsls(StyleMap, confs, evolve_path, xsl_path, work)
        # Only evolve-driver output is relevant for dryrun packaging
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"StyleMap processing failed: {e}")

    from zipfile import ZipFile, ZIP_DEFLATED

    mem_zip = work / "dryrun_xsls.zip"
    files_added = 0
    with ZipFile(mem_zip, "w", ZIP_DEFLATED) as zf:
        if effective_xsl and effective_xsl.exists():
            zf.write(effective_xsl, arcname=f"xsl/{effective_xsl.name}")
            files_added += 1
        if effective_evolve and effective_evolve.exists():
            zf.write(effective_evolve, arcname=f"xsl/{effective_evolve.name}")
            files_added += 1
        sm = work / "stylemap_manifest.json"
        if sm.exists():
            zf.write(sm, arcname=sm.name)
    if files_added == 0:
        raise HTTPException(status_code=400, detail="No effective XSLs generated (check StyleMap and conf)")
    return StreamingResponse(open(mem_zip, "rb"), media_type="application/zip", headers={"Content-Disposition": f"attachment; filename=dryrun_xsls.zip"})


# Helpers local to router
async def write_upload_stream(upload: UploadFile, dest: Path, max_bytes: int = 0):
    dest.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with open(dest, "wb") as out:
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if max_bytes and total > max_bytes:
                out.close()
                try:
                    dest.unlink(missing_ok=True)  # type: ignore[arg-type]
                except Exception:
                    pass
                raise HTTPException(status_code=413, detail="uploaded file exceeds size limit")
            out.write(chunk)
    try:
        await upload.close()
    except Exception:
        pass


def _safe_filename_from_url(url: str) -> str:
    try:
        from urllib.parse import urlparse

        p = urlparse(url)
        name = Path(p.path).name
        if not name:
            return "document.docx"
        if not name.lower().endswith(".docx"):
            name = f"{name}.docx"
        return safe_name(name)
    except Exception:
        return "document.docx"
