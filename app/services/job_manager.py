from __future__ import annotations

import json
import shutil
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
from typing import Optional

from app.core.config import Config
from app.core.cache import CacheStore, LockManager
from app.core.convert import compute_cache_key
from app.core.logging import log_line, console, log_exception
from app.core.proc import run_subprocess
from app.core.storage import compute_sha256
from app.core.tasks import TaskStore
from app.core.models import JobState


class JobManager:
    def __init__(self, cfg: Config, tasks: TaskStore, cache: CacheStore, locks: LockManager, workers: int = 2):
        self.cfg = cfg
        self.tasks = tasks
        self.cache = cache
        self.locks = locks
        self.pool = ThreadPoolExecutor(max_workers=workers)

    def create(self, debug: bool, img_post_proc: bool) -> JobState:
        task_id = str(uuid.uuid4())
        work_dir = self.cfg.data_root / "tasks" / task_id
        work_dir.mkdir(parents=True, exist_ok=True)
        js = JobState(
            task_id=task_id,
            state="pending",
            start_time=time.time(),
            debug=debug,
            img_post_proc=img_post_proc,
            work_dir=str(work_dir),
        )
        self.tasks.insert(js)
        return js

    def get(self, task_id: str) -> JobState:
        return self.tasks.get(task_id)

    def set_state(self, task_id: str, state: str, err: str = ""):
        self.tasks.set_state(task_id, state, err)

    # Schedules background job
    def submit(self, **kwargs):
        self.pool.submit(self._process_job, **kwargs)

    def _process_job(
        self,
        task_id: str,
        source_kind: str,
        source_value: str,
        debug: bool,
        img_post_proc: bool,
        conf_file: Optional[Path],
        custom_xsl: Optional[Path],
        custom_evolve: Optional[Path],
        mtef_source: Optional[str] = None,
        table_model: Optional[str] = None,
        fontmaps_dir: Optional[Path] = None,
        fontmaps_zip: Optional[Path] = None,
        job_cache_key: Optional[str] = None,
    ):
        js = self.get(task_id)
        work = Path(js.work_dir)
        log_path = self.cfg.log_dir / f"{task_id}.log"

        # Determine original filename and derived paths
        if source_kind == "file":
            orig_name = Path(source_value).name
        else:
            orig_name = source_value
        orig_name = orig_name or "document.docx"
        basename = Path(orig_name).stem

        out_tex = work / f"{basename}.tex"
        out_xml = work / f"{basename}.xml"
        debug_dir = work / f"{basename}.debug"

        try:
            self.set_state(task_id, "running")

            chosen_conf = conf_file if conf_file else (self.cfg.docx2tex_home / "conf" / "conf.xml")

            cache_key = job_cache_key or compute_cache_key(
                work / orig_name,
                chosen_conf,
                custom_xsl,
                custom_evolve,
                mtef_source,
                table_model,
                fontmaps_zip,
            )

            # Pre-check READY cache
            row = self.cache.get(cache_key)
            if row and int(row.get("available", 0)) == 1:
                cached_base = row.get("basename") or basename
                log_line(log_path, f"cache_hit key={cache_key} cached_base={cached_base} -> restore to {basename}")
                console(f"task={task_id} cache_hit key={cache_key}")
                try:
                    self.cache.restore_to_work(cache_key, cached_base, basename, Path(js.work_dir))
                except Exception:
                    # On restore failure, fall back to rebuild
                    pass
                self.cache.touch(cache_key)
            else:
                # Reserve cache and attempt build
                self.cache.reserve(cache_key)
                claimed = self.locks.claim(cache_key, task_id)
                if not claimed:
                    # Another builder -> wait for availability or takeover after stale
                    time.sleep(1.0)
                    row = self.cache.get(cache_key)
                    if row and int(row.get("available", 0)) == 1:
                        cached_base = row.get("basename") or basename
                        self.cache.restore_to_work(cache_key, cached_base, basename, Path(js.work_dir))
                        self.cache.touch(cache_key)
                    else:
                        # No published result; try to claim again
                        claimed = self.locks.claim(cache_key, task_id)
                if claimed:
                    # Build via Calabash
                    self.set_state(task_id, "converting")
                    env = {
                        "XML_CATALOG_FILES": str(self.cfg.catalog_file),
                        "PATH": os.environ.get("PATH", ""),
                        "JAVA_TOOL_OPTIONS": os.environ.get("JAVA_TOOL_OPTIONS", ""),
                    }
                    cmd = [str(self.cfg.docx2tex_home / "calabash" / "calabash.sh"), str(self.cfg.docx2tex_home / "xpl" / "docx2tex.xpl")]
                    cmd.extend(["-i", f"source=file://{(work / orig_name).as_posix()}"])
                    cmd.extend(["-p", f"conf={(self.cfg.docx2tex_home / 'conf' / 'conf.xml').as_uri()}"])
                    cmd.extend(["-o", f"result=file://{(out_tex).as_posix()}"])

                    rc, out, err = run_subprocess(cmd, cwd=self.cfg.docx2tex_home, env=env, timeout=1200)
                    with open(log_path, "ab") as lf:
                        lf.write(b"\n--- calabash ---\n")
                        lf.write((out or "").encode("utf-8") + b"\n" + (err or "").encode("utf-8"))
                    if rc != 0 or not out_tex.exists():
                        self.set_state(task_id, "failed", err or "docx2tex failed")
                        console(f"task={task_id} stage=docx2tex_failed")
                        return
                    # Cache publish
                    try:
                        self.cache.save_to_disk(cache_key, basename, Path(js.work_dir))
                        self.cache.put(cache_key, basename)
                        log_line(log_path, f"cache_saved key={cache_key} base={basename}")
                        console(f"task={task_id} cache_saved key={cache_key}")
                    except Exception as e:
                        log_exception(log_path, "cache_save_failed", e)
                    finally:
                        self.locks.release(cache_key)

            # Vector image conversion (optional)
            if img_post_proc and out_tex.exists():
                self.set_state(task_id, "converting")
                from app.core.proc import run_subprocess as run2

                conv_script = self.cfg.app_home / "scripts" / "convert_vector_images.py"
                rc2, out2, err2 = run2(["python3", str(conv_script), str(out_tex)], timeout=600)
                with open(log_path, "ab") as lf:
                    lf.write(b"\n--- convert_vector_images ---\n")
                    lf.write((out2 or "").encode("utf-8") + b"\n" + (err2 or "").encode("utf-8"))

            # Packaging
            self.set_state(task_id, "packaging")
            from zipfile import ZipFile, ZIP_DEFLATED

            result_zip_public = self.cfg.public_root / f"{basename}.zip"
            log_line(log_path, f"packaging -> {result_zip_public}")
            console(f"task={task_id} stage=packaging zip={result_zip_public}")
            manifest = {
                "task_id": task_id,
                "debug": debug,
                "start_time": js.start_time,
                "end_time": time.time(),
                "files": [],
                "mtef_source": (mtef_source or ""),
                "table_model": (table_model or ""),
                "fontmaps_dir": str(fontmaps_dir) if fontmaps_dir else "",
            }
            self.cfg.public_root.mkdir(parents=True, exist_ok=True)
            with ZipFile(result_zip_public, "w", ZIP_DEFLATED) as zf:
                if debug:
                    for p in [out_tex, out_xml]:
                        if p.exists():
                            zf.write(p, arcname=p.name)
                            manifest["files"].append(p.name)
                    csv_path = work / f"{basename}.csv"
                    if csv_path.exists():
                        zf.write(csv_path, arcname=csv_path.name)
                        manifest["files"].append(csv_path.name)
                    if (work / f"{basename}.debug").exists():
                        for sub in (work / f"{basename}.debug").rglob("*"):
                            if sub.is_file():
                                arc = f"{(work / f'{basename}.debug').name}/{sub.relative_to(work / f'{basename}.debug')}"
                                zf.write(sub, arcname=arc)
                                manifest["files"].append(arc)
                    tmp_dir = work / f"{basename}.docx.tmp"
                    if tmp_dir.exists():
                        for sub in tmp_dir.rglob("*"):
                            if sub.is_file():
                                arc = f"{tmp_dir.name}/{sub.relative_to(tmp_dir)}"
                                zf.write(sub, arcname=arc)
                                manifest["files"].append(arc)
                else:
                    if out_tex.exists():
                        zf.write(out_tex, arcname=out_tex.name)
                        manifest["files"].append(out_tex.name)
                    image_dir = work / "image"
                    if image_dir.exists():
                        for sub in image_dir.rglob("*"):
                            if sub.is_file():
                                arc = f"image/{sub.relative_to(image_dir)}"
                                zf.write(sub, arcname=arc)
                                manifest["files"].append(arc)
                zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

            self.set_state(task_id, "done")
            log_line(log_path, "task_done")
            console(f"task={task_id} stage=done")
        except Exception as e:
            log_line(log_path, f"task_failed: {e}")
            self.set_state(task_id, "failed", str(e))
            console(f"task={task_id} stage=failed error={e}")
