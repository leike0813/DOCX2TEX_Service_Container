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
from app.core.postprocess import (
    release_collect_images_and_normalize,
    debug_comment_vsdx_and_normalize,
)
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
        no_cache: bool = False,
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
            if (not no_cache) and row and int(row.get("available", 0)) == 1:
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
                # Build path (optionally guarded by lock when using cache)
                claimed = True
                if not no_cache:
                    claimed = self.locks.claim(cache_key, task_id)
                    if not claimed:
                        time.sleep(1.0)
                        row = self.cache.get(cache_key)
                        if row and int(row.get("available", 0)) == 1:
                            cached_base = row.get("basename") or basename
                            self.cache.restore_to_work(cache_key, cached_base, basename, Path(js.work_dir))
                            self.cache.touch(cache_key)
                            claimed = False
                if claimed:
                    # Build via Calabash
                    self.set_state(task_id, "converting")
                    env = {
                        "XML_CATALOG_FILES": str(self.cfg.catalog_file),
                        "PATH": os.environ.get("PATH", ""),
                        "JAVA_TOOL_OPTIONS": os.environ.get("JAVA_TOOL_OPTIONS", ""),
                    }
                    cmd = [
                        str(self.cfg.docx2tex_home / "calabash" / "calabash.sh"),
                    ]
                    option_args: list[str] = []
                    # required docx option (expects file URI)
                    option_args.append(f"docx={(work / orig_name).resolve().as_uri()}")
                    # xml2tex configuration (uploaded or default)
                    option_args.append(f"conf={chosen_conf.as_uri()}")
                    # optional: custom evolve driver (effective from StyleMap or user upload)
                    if custom_evolve and Path(custom_evolve).exists():
                        # docx2tex.xpl expects this as an input port
                        cmd.extend(["-i", f"custom-evolve-hub-driver={(Path(custom_evolve).resolve().as_uri())}"])
                    # optional: user-provided custom XSL between evolve and xml2tex
                    if custom_xsl and Path(custom_xsl).exists():
                        option_args.append(f"custom-xsl={(Path(custom_xsl).resolve().as_uri())}")
                    # optional MathType/Calstable settings
                    if mtef_source:
                        option_args.append(f"mtef-source={mtef_source}")
                    if table_model:
                        option_args.append(f"table-model={table_model}")
                    if fontmaps_dir and Path(fontmaps_dir).exists():
                        option_args.append(f"custom-font-maps-dir={Path(fontmaps_dir).resolve().as_uri()}")
                    # toggle docx2tex debug mode + directory so artifacts go under work/<basename>.debug
                    option_args.append(f"debug={'yes' if debug else 'no'}")
                    option_args.append(f"debug-dir-uri={debug_dir.resolve().as_uri()}")
                    # output
                    cmd.extend(["-o", f"result={out_tex.resolve().as_uri()}"])
                    cmd.extend(["-o", f"hub={out_xml.resolve().as_uri()}"])
                    # Pipeline document must be last per Calabash CLI rules
                    cmd.append(str(self.cfg.docx2tex_home / "xpl" / "docx2tex.xpl"))
                    cmd.extend(option_args)

                    # Log constructed command for troubleshooting
                    try:
                        import shlex
                        with open(log_path, "ab") as lf:
                            lf.write(b"\n--- calabash_cmd ---\n")
                            lf.write((" ".join(shlex.quote(x) for x in cmd) + "\n").encode("utf-8"))
                    except Exception:
                        pass

                    rc, out, err = run_subprocess(cmd, cwd=self.cfg.docx2tex_home, env=env, timeout=1200)
                    with open(log_path, "ab") as lf:
                        lf.write(b"\n--- calabash ---\n")
                        lf.write((out or "").encode("utf-8") + b"\n" + (err or "").encode("utf-8"))
                    if rc != 0 or not out_tex.exists():
                        # hard fail; cleanup any partial cache artifacts and release lock
                        try:
                            if not no_cache:
                                self.cache.mark_gone(cache_key)
                                # remove on-disk partials
                                import shutil
                                shutil.rmtree(self.cache.cache_dir(cache_key), ignore_errors=True)
                        except Exception:
                            pass
                        if not no_cache:
                            self.locks.release(cache_key)
                        self.set_state(task_id, "failed", err or "docx2tex failed")
                        console(f"task={task_id} stage=docx2tex_failed")
                        return
                    # Cache publish
                    if not no_cache:
                        try:
                            self.cache.save_to_disk(cache_key, basename, Path(js.work_dir))
                            self.cache.put(cache_key, basename)
                            log_line(log_path, f"cache_saved key={cache_key} base={basename}")
                            console(f"task={task_id} cache_saved key={cache_key}")
                        except Exception as e:
                            log_exception(log_path, "cache_save_failed", e)
                        finally:
                            self.locks.release(cache_key)

            # Vector image conversion (optional, in-process)
            if img_post_proc and out_tex.exists():
                self.set_state(task_id, "converting")
                try:
                    from app.core.postprocess import convert_vector_references
                    c, m, f = convert_vector_references(out_tex)
                    with open(log_path, "ab") as lf:
                        lf.write(b"\n--- convert_vector_images ---\n")
                        lf.write(f"converted={c} missing={m} failed={f}\n".encode("utf-8"))
                except Exception as e:
                    with open(log_path, "ab") as lf:
                        lf.write(b"\n--- convert_vector_images (error) ---\n")
                        lf.write(str(e).encode("utf-8"))

            try:
                # Packaging (require valid main TeX or debug artifacts)
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
                        # debug-mode: tidy TeX, comment .vsdx, normalize width
                        try:
                            _ = debug_comment_vsdx_and_normalize(out_tex)
                        except Exception:
                            pass
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
                        # include log
                        if log_path.exists():
                            arc = f"logs/{log_path.name}"
                            zf.write(log_path, arcname=arc)
                            manifest["files"].append(arc)
                        # include effective custom evolve xsl & stylemap manifest if present
                        eff = work / "custom-evolve-effective.xsl"
                        if eff.exists():
                            zf.write(eff, arcname=f"xsl/{eff.name}")
                            manifest["files"].append(f"xsl/{eff.name}")
                        sm = work / "stylemap_manifest.json"
                        if sm.exists():
                            zf.write(sm, arcname=sm.name)
                            manifest["files"].append(sm.name)
                    else:
                        # non-debug: collect images, rewrite paths, drop .vsdx, normalize width
                        try:
                            image_dir = work / "image"
                            ncol, ndrop = release_collect_images_and_normalize(out_tex, image_dir)
                        except Exception:
                            pass
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

                # Sanity: if no meaningful files were added (e.g., calabash produced nothing), fail the task
                if not debug and not out_tex.exists():
                    self.set_state(task_id, "failed", "no output produced")
                    console(f"task={task_id} stage=packaging_failed no_output")
                    return

                self.set_state(task_id, "done")
                log_line(log_path, "task_done")
                console(f"task={task_id} stage=done")
            except Exception as e:
                log_line(log_path, f"task_failed: {e}")
                self.set_state(task_id, "failed", str(e))
                console(f"task={task_id} stage=failed error={e}")
                return
        except Exception as e:
            log_line(log_path, f"task_failed: {e}")
            self.set_state(task_id, "failed", str(e))
            console(f"task={task_id} stage=failed error={e}")
