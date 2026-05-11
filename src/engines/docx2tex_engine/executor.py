from __future__ import annotations

import shutil
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from document_conversion.infrastructure.cache import CacheStore, LockManager
from document_conversion.infrastructure.config import Config
from document_conversion.infrastructure.logging import console, log_exception, log_line
from document_conversion.infrastructure.state import JobState, TaskStore

from .convert import compute_cache_key
from .packaging import ArtifactPackager
from .runner import Docx2TexRunner, RunnerRequest


@dataclass(frozen=True)
class TaskExecutionRequest:
    task_id: str
    source_kind: str
    source_value: str
    debug: bool
    img_post_proc: bool
    conf_file: Path | None
    custom_xsl: Path | None
    custom_evolve: Path | None
    mtef_source: str | None = None
    table_model: str | None = None
    fontmaps_dir: Path | None = None
    fontmaps_zip: Path | None = None
    job_cache_key: str | None = None
    no_cache: bool = False
    image_dir: str = "image"


class TaskExecutor:
    def __init__(
        self,
        cfg: Config,
        tasks: TaskStore,
        cache: CacheStore,
        locks: LockManager,
        workers: int = 2,
    ):
        self.cfg = cfg
        self.tasks = tasks
        self.cache = cache
        self.locks = locks
        self.pool = ThreadPoolExecutor(max_workers=workers)
        self.runner = Docx2TexRunner(cfg)
        self.packager = ArtifactPackager(cfg.public_root)

    def create(self, debug: bool, img_post_proc: bool) -> JobState:
        task_id = str(uuid.uuid4())
        work_dir = self.cfg.data_root / "tasks" / task_id
        work_dir.mkdir(parents=True, exist_ok=True)
        job_state = JobState(
            task_id=task_id,
            state="pending",
            start_time=time.time(),
            debug=debug,
            img_post_proc=img_post_proc,
            work_dir=str(work_dir),
        )
        self.tasks.insert(job_state)
        return job_state

    def get(self, task_id: str) -> JobState:
        return self.tasks.get(task_id)

    def set_state(self, task_id: str, state: str, err: str = "") -> None:
        self.tasks.set_state(task_id, state, err)

    def submit(self, **kwargs) -> None:
        self.pool.submit(self._process_job, TaskExecutionRequest(**kwargs))

    def _process_job(self, request: TaskExecutionRequest) -> None:
        job_state = self.get(request.task_id)
        work_dir = Path(job_state.work_dir)
        log_path = self.cfg.log_dir / f"{request.task_id}.log"
        orig_name = (
            Path(request.source_value).name
            if request.source_kind == "file"
            else request.source_value
        )
        orig_name = orig_name or "document.docx"
        try:
            self.set_state(request.task_id, "running")
            chosen_conf = request.conf_file or (self.cfg.docx2tex_home / "conf" / "conf.xml")
            cache_key = request.job_cache_key or compute_cache_key(
                work_dir / orig_name,
                chosen_conf,
                request.custom_xsl,
                request.custom_evolve,
                request.mtef_source,
                request.table_model,
                request.fontmaps_zip,
            )
            basename = Path(orig_name).stem
            out_tex = work_dir / f"{basename}.tex"
            out_xml = work_dir / f"{basename}.xml"
            row = self.cache.get(cache_key)
            if (not request.no_cache) and row and int(row.get("available", 0)) == 1:
                cached_base = row.get("basename") or basename
                log_line(
                    log_path,
                    (
                        f"cache_hit key={cache_key} cached_base={cached_base} "
                        f"-> restore to {basename}"
                    ),
                )
                console(f"task={request.task_id} cache_hit key={cache_key}")
                try:
                    self.cache.restore_to_work(cache_key, cached_base, basename, work_dir)
                except Exception:
                    pass
                self.cache.touch(cache_key)
            else:
                claimed = True
                if not request.no_cache:
                    claimed = self.locks.claim(cache_key, request.task_id)
                    if not claimed:
                        time.sleep(1.0)
                        row = self.cache.get(cache_key)
                        if row and int(row.get("available", 0)) == 1:
                            cached_base = row.get("basename") or basename
                            self.cache.restore_to_work(cache_key, cached_base, basename, work_dir)
                            self.cache.touch(cache_key)
                            claimed = False
                if claimed:
                    self.set_state(request.task_id, "converting")
                    try:
                        output = self.runner.run(
                            RunnerRequest(
                                work_dir=work_dir,
                                orig_name=orig_name,
                                debug=request.debug,
                                conf_file=request.conf_file,
                                custom_xsl=request.custom_xsl,
                                custom_evolve=request.custom_evolve,
                                mtef_source=request.mtef_source,
                                table_model=request.table_model,
                                fontmaps_dir=request.fontmaps_dir,
                            ),
                            log_path,
                        )
                    except Exception as exc:
                        if not request.no_cache:
                            try:
                                self.cache.mark_gone(cache_key)
                                shutil.rmtree(self.cache.cache_dir(cache_key), ignore_errors=True)
                            except Exception:
                                pass
                            self.locks.release(cache_key)
                        self.set_state(request.task_id, "failed", str(exc))
                        console(f"task={request.task_id} stage=docx2tex_failed")
                        return
                    basename = output.basename
                    out_tex = output.out_tex
                    out_xml = output.out_xml
                    if not request.no_cache:
                        try:
                            self.cache.save_to_disk(cache_key, basename, work_dir)
                            self.cache.put(cache_key, basename)
                            log_line(log_path, f"cache_saved key={cache_key} base={basename}")
                            console(f"task={request.task_id} cache_saved key={cache_key}")
                        except Exception as exc:
                            log_exception(log_path, "cache_save_failed", exc)
                        finally:
                            self.locks.release(cache_key)
            self.set_state(request.task_id, "packaging")
            self.packager.package(
                task_id=request.task_id,
                job_state=job_state,
                basename=basename,
                work_dir=work_dir,
                out_tex=out_tex,
                out_xml=out_xml,
                debug=request.debug,
                img_post_proc=request.img_post_proc,
                image_dir=request.image_dir,
                log_path=log_path,
                mtef_source=request.mtef_source,
                table_model=request.table_model,
                fontmaps_dir=request.fontmaps_dir,
            )
            self.set_state(request.task_id, "done")
            log_line(log_path, "task_done")
            console(f"task={request.task_id} stage=done")
        except Exception as exc:
            log_line(log_path, f"task_failed: {exc}")
            self.set_state(request.task_id, "failed", str(exc))
            console(f"task={request.task_id} stage=failed error={exc}")
