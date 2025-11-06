import io
import json
import logging
import os
import shutil
import threading
import time
import uuid
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, Optional

import requests
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel


# Paths and env
APP_HOME = Path(os.environ.get("APP_HOME", "/app")).resolve()
# DATA_ROOT: 私有挂载卷，用于上传、缓存、数据库、任务中间文件
DATA_ROOT = Path(os.environ.get("DATA_ROOT", "/data")).resolve()
# PUBLIC_ROOT: 对外可挂载目录，仅放最终结果（zip）
PUBLIC_ROOT = Path(os.environ.get("WORK_ROOT", "/work")).resolve()
LOG_DIR = Path(os.environ.get("LOG_DIR", "/var/log/docx2tex")).resolve()
DOCX2TEX_HOME = Path(os.environ.get("DOCX2TEX_HOME", "/opt/docx2tex")).resolve()
CATALOG_FILE = Path(os.environ.get("XML_CATALOG_FILES", "/opt/catalog/catalog.xml")).resolve()
DB_PATH = Path(os.environ.get("STATE_DB", str(DATA_ROOT / "state.db"))).resolve()
try:
    MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", "0"))
except ValueError:
    MAX_UPLOAD_BYTES = 0

CALABASH = DOCX2TEX_HOME / "calabash" / "calabash.sh"
DOCX2TEX_XPL = DOCX2TEX_HOME / "xpl" / "docx2tex.xpl"
DEFAULT_CONF = DOCX2TEX_HOME / "conf" / "conf.xml"


app = FastAPI(title="docx2tex-service")


class JobState(BaseModel):
    task_id: str
    state: str
    err_msg: str = ""
    start_time: float
    end_time: Optional[float] = None
    debug: bool = False
    img_post_proc: bool = True
    work_dir: str
    sha256: Optional[str] = None


def _db_connect():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # improve concurrency
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn


def _db_init():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _db_connect() as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
              task_id TEXT PRIMARY KEY,
              state TEXT NOT NULL,
              err_msg TEXT DEFAULT '',
              start_time REAL NOT NULL,
              end_time REAL,
              debug INTEGER NOT NULL,
              img_post_proc INTEGER NOT NULL,
              work_dir TEXT NOT NULL,
              created REAL NOT NULL,
              sha256 TEXT
            );
            """
        )
        con.commit()
        # Add columns if upgrading from an earlier schema
        # Cache table
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS caches (
              cache_key TEXT PRIMARY KEY,
              basename TEXT NOT NULL,
              created REAL NOT NULL,
              last_access REAL NOT NULL,
              available INTEGER NOT NULL DEFAULT 1
            );
            """
        )
        # Add last_access column if missing
        try:
            con.execute("ALTER TABLE caches ADD COLUMN last_access REAL")
        except Exception:
            pass
        # Locks table (for coordinating cache builds)
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS locks (
              cache_key TEXT PRIMARY KEY,
              builder   TEXT,
              started   REAL
            );
            """
        )
        con.commit()


def _row_to_jobstate(row: sqlite3.Row) -> JobState:
    return JobState(
        task_id=row["task_id"],
        state=row["state"],
        err_msg=row["err_msg"] or "",
        start_time=row["start_time"],
        end_time=row["end_time"],
        debug=bool(row["debug"]),
        img_post_proc=bool(row["img_post_proc"]),
        work_dir=row["work_dir"],
    )


def _db_insert_task(js: JobState):
    with _db_connect() as con:
        con.execute(
            "INSERT INTO tasks(task_id,state,err_msg,start_time,end_time,debug,img_post_proc,work_dir,created,sha256) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                js.task_id,
                js.state,
                js.err_msg,
                js.start_time,
                js.end_time,
                1 if js.debug else 0,
                1 if js.img_post_proc else 0,
                js.work_dir,
                time.time(),
                js.sha256,
            ),
        )
        con.commit()


def _db_get_task(task_id: str) -> JobState:
    with _db_connect() as con:
        cur = con.execute("SELECT * FROM tasks WHERE task_id=?", (task_id,))
        row = cur.fetchone()
        if not row:
            raise KeyError(task_id)
        return _row_to_jobstate(row)


def _db_update_state(task_id: str, state: str, err: str = ""):
    with _db_connect() as con:
        end_time = time.time() if state in ("done", "failed") else None
        if end_time is None:
            con.execute("UPDATE tasks SET state=?, err_msg=? WHERE task_id=?", (state, err, task_id))
        else:
            con.execute("UPDATE tasks SET state=?, err_msg=?, end_time=? WHERE task_id=?", (state, err, end_time, task_id))
        con.commit()


def _db_set_sha(task_id: str, sha: str):
    with _db_connect() as con:
        con.execute("UPDATE tasks SET sha256=? WHERE task_id=?", (sha, task_id))
        con.commit()


def _db_cache_get(key: str) -> Optional[Dict[str, str]]:
    try:
        with _db_connect() as con:
            cur = con.execute("SELECT cache_key, basename, available FROM caches WHERE cache_key=?", (key,))
            row = cur.fetchone()
            if not row:
                return None
            return {"cache_key": row["cache_key"], "basename": row["basename"], "available": row["available"]}
    except sqlite3.OperationalError as e:
        if "no such table" in str(e).lower():
            _db_init()
            try:
                with _db_connect() as con:
                    cur = con.execute("SELECT cache_key, basename, available FROM caches WHERE cache_key=?", (key,))
                    row = cur.fetchone()
                    if not row:
                        return None
                    return {"cache_key": row["cache_key"], "basename": row["basename"], "available": row["available"]}
            except Exception:
                return None
        return None


def _db_cache_put(key: str, basename: str):
    try:
        with _db_connect() as con:
            now = time.time()
            con.execute("INSERT OR REPLACE INTO caches(cache_key, basename, created, last_access, available) VALUES(?,?,?,?,1)", (key, basename, now, now))
            con.commit()
    except sqlite3.OperationalError as e:
        if "no such table" in str(e).lower():
            _db_init()
            with _db_connect() as con:
                now = time.time()
                con.execute("INSERT OR REPLACE INTO caches(cache_key, basename, created, last_access, available) VALUES(?,?,?,?,1)", (key, basename, now, now))
                con.commit()
        else:
            raise


def _db_cache_mark_gone(key: str):
    try:
        with _db_connect() as con:
            con.execute("UPDATE caches SET available=0 WHERE cache_key=?", (key,))
            con.commit()
    except sqlite3.OperationalError as e:
        if "no such table" in str(e).lower():
            _db_init()
        # ignore otherwise


def _db_cache_reserve(key: str):
    """Ensure a caches row exists; mark as available=0 when first reserved.
    Return current row dict {cache_key, basename, available}.
    """
    try:
        with _db_connect() as con:
            now = time.time()
            con.execute(
                "INSERT OR IGNORE INTO caches(cache_key, basename, created, last_access, available) VALUES(?,?,?,?,0)",
                (key, "", now, now),
            )
            con.commit()
            cur = con.execute("SELECT cache_key, basename, available FROM caches WHERE cache_key=?", (key,))
            row = cur.fetchone()
            if not row:
                return None
            return {"cache_key": row["cache_key"], "basename": row["basename"], "available": row["available"]}
    except sqlite3.OperationalError as e:
        if "no such table" in str(e).lower():
            _db_init()
            return _db_cache_reserve(key)
        return None


def _db_cache_publish(key: str, basename: str):
    try:
        with _db_connect() as con:
            now = time.time()
            con.execute("UPDATE caches SET basename=?, available=1, created=?, last_access=? WHERE cache_key=?", (basename, now, now, key))
            con.commit()
    except sqlite3.OperationalError as e:
        if "no such table" in str(e).lower():
            _db_init()
            with _db_connect() as con:
                now = time.time()
                con.execute("UPDATE caches SET basename=?, available=1, created=?, last_access=? WHERE cache_key=?", (basename, now, now, key))
                con.commit()
        else:
            raise


def _db_cache_touch(key: str):
    with _db_connect() as con:
        con.execute("UPDATE caches SET last_access=? WHERE cache_key=?", (time.time(), key))
        con.commit()


def _db_lock_claim(key: str, builder: str) -> bool:
    try:
        with _db_connect() as con:
            con.execute("INSERT INTO locks(cache_key,builder,started) VALUES(?,?,?)", (key, builder, time.time()))
            con.commit()
            return True
    except sqlite3.IntegrityError:
        return False
    except sqlite3.OperationalError as e:
        if "no such table" in str(e).lower():
            _db_init()
            try:
                with _db_connect() as con:
                    con.execute("INSERT INTO locks(cache_key,builder,started) VALUES(?,?,?)", (key, builder, time.time()))
                    con.commit()
                    return True
            except Exception:
                return False
        return False
    except Exception:
        return False


def _db_lock_release(key: str):
    try:
        with _db_connect() as con:
            con.execute("DELETE FROM locks WHERE cache_key=?", (key,))
            con.commit()
    except sqlite3.OperationalError as e:
        if "no such table" in str(e).lower():
            _db_init()
            try:
                with _db_connect() as con:
                    con.execute("DELETE FROM locks WHERE cache_key=?", (key,))
                    con.commit()
            except Exception:
                pass
    except Exception:
        pass


def _db_lock_get(key: str) -> Optional[dict]:
    try:
        with _db_connect() as con:
            cur = con.execute("SELECT cache_key,builder,started FROM locks WHERE cache_key=?", (key,))
            row = cur.fetchone()
            if not row:
                return None
            return {"cache_key": row["cache_key"], "builder": row["builder"], "started": row["started"]}
    except sqlite3.OperationalError as e:
        if "no such table" in str(e).lower():
            _db_init()
            try:
                with _db_connect() as con:
                    cur = con.execute("SELECT cache_key,builder,started FROM locks WHERE cache_key=?", (key,))
                    row = cur.fetchone()
                    if not row:
                        return None
                    return {"cache_key": row["cache_key"], "builder": row["builder"], "started": row["started"]}
            except Exception:
                return None
        return None


def cleanup_locks(max_age_sec: int):
    if max_age_sec <= 0:
        return
    now = time.time()
    with _db_connect() as con:
        cur = con.execute("SELECT cache_key, started FROM locks")
        rows = cur.fetchall()
    for row in rows:
        started = row["started"] or 0
        if now - started > max_age_sec:
            _db_lock_release(row["cache_key"])


def start_lock_sweeper(interval_sec: int, max_age_sec: int):
    if interval_sec <= 0:
        return
    def loop():
        while True:
            try:
                cleanup_locks(max_age_sec)
            except Exception:
                pass
            time.sleep(max(1, interval_sec))
    t = threading.Thread(target=loop, name="lock-sweeper", daemon=True)
    t.start()


def _log_line(log_path: Path, msg: str):
    try:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {msg}\n"
        with open(log_path, "ab") as lf:
            lf.write(line.encode("utf-8", errors="ignore"))
    except Exception:
        # best-effort logging
        pass


def _console(msg: str):
    try:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{ts}] {msg}", flush=True)
    except Exception:
        pass


def _log_exception(log_path: Path, prefix: str, exc: Exception):
    try:
        _log_line(log_path, f"{prefix}: {exc}")
        _console(f"{prefix}: {exc}")
    except Exception:
        pass


def compute_sha256(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_cache_key(docx: Path, conf: Optional[Path], xsl: Optional[Path]) -> str:
    import hashlib
    h = hashlib.sha256()
    # docx
    with open(docx, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    # conf (use default if None)
    conf_path = conf if conf else DEFAULT_CONF
    with open(conf_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 512), b""):
            h.update(b"|CONF|")
            h.update(chunk)
    # xsl (optional)
    if xsl and xsl.exists():
        with open(xsl, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 512), b""):
                h.update(b"|XSL|")
                h.update(chunk)
    else:
        h.update(b"|XSL|NONE")
    return h.hexdigest()


def _cache_dir(key: str) -> Path:
    return (DATA_ROOT / "cache" / key).resolve()


def _cache_meta_path(key: str) -> Path:
    return _cache_dir(key) / "meta.json"


def _cache_meta(key: str) -> Optional[dict]:
    meta = _cache_meta_path(key)
    if not meta.exists():
        return None
    try:
        return json.loads(meta.read_text(encoding="utf-8"))
    except Exception:
        return None


def _cache_disk_ok(key: str) -> Optional[str]:
    """Check if cache directory exists on disk and looks complete.
    Returns basename if OK, else None.
    """
    try:
        m = _cache_meta(key)
        if not m:
            return None
        base = m.get("basename")
        if not base:
            return None
        d = _cache_dir(key)
        required = [d / f"{base}.tex", d / f"{base}.xml", d / f"{base}.debug", d / f"{base}.docx.tmp"]
        for p in required:
            if not Path(p).exists():
                return None
        return base
    except Exception:
        return None


def _cache_save(key: str, basename: str, work: Path):
    d = _cache_dir(key)
    d.mkdir(parents=True, exist_ok=True)
    # copy tex, xml, csv, debug dir, docx.tmp dir
    for fn in (f"{basename}.tex", f"{basename}.xml", f"{basename}.csv"):
        p = work / fn
        if p.exists():
            shutil.copy2(p, d / fn)
    src_debug = work / f"{basename}.debug"
    if src_debug.exists():
        dst_debug = d / src_debug.name
        if dst_debug.exists():
            shutil.rmtree(dst_debug, ignore_errors=True)
        shutil.copytree(src_debug, dst_debug)
    src_tmp = work / f"{basename}.docx.tmp"
    if src_tmp.exists():
        dst_tmp = d / src_tmp.name
        if dst_tmp.exists():
            shutil.rmtree(dst_tmp, ignore_errors=True)
        shutil.copytree(src_tmp, dst_tmp)
    meta = {"key": key, "basename": basename, "created": time.time()}
    _atomic_write_json(_cache_meta_path(key), meta)


def _atomic_write_json(path: Path, data: dict):
    """Write JSON atomically to the given path.
    Creates parent dirs, writes to a temp file in the same directory, then renames.
    Safe across platforms (close file before replace).
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        # Write JSON with UTF-8, ensure_ascii=False for readability
        s = json.dumps(data, ensure_ascii=False, indent=2)
        tmp.write_text(s, encoding="utf-8")
        # Replace is atomic on POSIX; on Windows it overwrites existing file
        tmp.replace(path)
    except Exception as e:
        # Best effort: fall back to direct write
        try:
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            raise e


def _cache_restore(key: str, cached_base: str, new_base: str, dest: Path):
    d = _cache_dir(key)
    # files
    for ext in ("tex", "xml", "csv"):
        src = d / f"{cached_base}.{ext}"
        if src.exists():
            dst = dest / f"{new_base}.{ext}"
            shutil.copy2(src, dst)
            if ext == "tex":
                # rewrite references to .docx.tmp folder name
                try:
                    s = dst.read_text(encoding="utf-8", errors="replace")
                    s = s.replace(f"{cached_base}.docx.tmp", f"{new_base}.docx.tmp")
                    dst.write_text(s, encoding="utf-8")
                except Exception:
                    pass
    # debug dir
    src_debug = d / f"{cached_base}.debug"
    if src_debug.exists():
        dst_debug = dest / f"{new_base}.debug"
        if dst_debug.exists():
            shutil.rmtree(dst_debug, ignore_errors=True)
        shutil.copytree(src_debug, dst_debug)
    # tmp dir
    src_tmp = d / f"{cached_base}.docx.tmp"
    if src_tmp.exists():
        dst_tmp = dest / f"{new_base}.docx.tmp"
        if dst_tmp.exists():
            shutil.rmtree(dst_tmp, ignore_errors=True)
        shutil.copytree(src_tmp, dst_tmp)


def _strip_ns(tag: str) -> str:
    return tag.split('}', 1)[1] if tag.startswith('{') else tag


def _maybe_rewrite_conf_imports(conf_path: Path) -> bool:
    """If user's uploaded xml2tex conf contains <import href="conf.xml"/>,
    rewrite it to the container default conf absolute URI so it doesn't depend
    on being placed under docx2tex/conf.

    Returns True if a rewrite was performed.
    """
    target_uri = DEFAULT_CONF.resolve().as_uri()
    changed = False
    # Try XML parse first
    try:
        from xml.etree import ElementTree as ET
        tree = ET.parse(conf_path)
        root = tree.getroot()
        for el in root.iter():
            if _strip_ns(el.tag) == 'import':
                href = (el.get('href') or '').strip()
                # Only rewrite relative/conf.xml style references
                if href and '://' not in href and href.lower().endswith('conf.xml'):
                    el.set('href', target_uri)
                    changed = True
        if changed:
            tree.write(conf_path, encoding='utf-8', xml_declaration=True)
            _console(f"rewrite_conf_import: set import@href -> {target_uri}")
            return True
    except Exception:
        pass
    # Fallback: textual replace (minimal, safe)
    try:
        s = conf_path.read_text(encoding='utf-8', errors='ignore')
        s2 = s.replace('href="conf.xml"', f'href="{target_uri}"').replace("href='conf.xml'", f"href='{target_uri}'")
        if s2 != s:
            conf_path.write_text(s2, encoding='utf-8')
            _console(f"rewrite_conf_import(text): set import@href -> {target_uri}")
            return True
    except Exception:
        pass
    return False


class JobManager:
    def __init__(self, workers: int = 2):
        self.lock = threading.Lock()
        self.pool = ThreadPoolExecutor(max_workers=workers)

    def create(self, debug: bool, img_post_proc: bool) -> JobState:
        with self.lock:
            task_id = str(uuid.uuid4())
        work_dir = DATA_ROOT / "tasks" / task_id
        work_dir.mkdir(parents=True, exist_ok=True)
        js = JobState(
            task_id=task_id,
            state="pending",
            start_time=time.time(),
            debug=debug,
            img_post_proc=img_post_proc,
            work_dir=str(work_dir),
        )
        _db_insert_task(js)
        return js

    def get(self, task_id: str) -> JobState:
        return _db_get_task(task_id)

    def set_state(self, task_id: str, state: str, err: str = ""):
        _db_update_state(task_id, state, err)


jobs = JobManager()


def to_file_uri(p: Path) -> str:
    return p.resolve().as_uri()


def write_bytes(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


async def write_upload_stream(upload: UploadFile, dest: Path, max_bytes: int = 0):
    dest.parent.mkdir(parents=True, exist_ok=True)
    total = 0
    with open(dest, "wb") as out:
        while True:
            chunk = await upload.read(1024 * 1024)  # 1 MiB chunks
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


def download_to(path: Path, url: str):
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    write_bytes(path, r.content)


def run_subprocess(cmd: list[str], cwd: Optional[Path] = None, env: Optional[dict] = None, timeout: int = 600) -> tuple[int, str, str]:
    import subprocess

    proc = subprocess.Popen(cmd, cwd=str(cwd) if cwd else None, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
    try:
        out, err = proc.communicate(timeout=timeout)
        return proc.returncode, out, err
    except subprocess.TimeoutExpired:
        proc.kill()
        out, err = proc.communicate()
        return 124, out, err


def safe_name(name: str) -> str:
    return "".join(ch if ch.isalnum() or ch in (".", "_", "-", "+") else "_" for ch in name)


def is_mountpoint(path: Path) -> bool:
    try:
        target = str(path.resolve())
        with open("/proc/self/mountinfo", "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) >= 5:
                    mnt = parts[4]
                    if mnt == target:
                        return True
    except Exception:
        pass
    return False


def cleanup_old_jobs(retention_days: int):
    if retention_days <= 0:
        return
    cutoff = time.time() - retention_days * 86400
    # find old tasks in DB
    ids_to_purge: list[str] = []
    with _db_connect() as con:
        cur = con.execute(
            "SELECT task_id, COALESCE(end_time, start_time) AS t FROM tasks WHERE state IN ('done','failed')"
        )
        for row in cur.fetchall():
            if row["t"] < cutoff:
                ids_to_purge.append(row["task_id"])
        # delete db rows after filesystem cleanup below
    for tid in ids_to_purge:
        d = DATA_ROOT / "tasks" / tid
        if d.exists():
            try:
                shutil.rmtree(d, ignore_errors=True)
            except Exception:
                pass
        log_path = LOG_DIR / f"{tid}.log"
        if log_path.exists() and log_path.stat().st_mtime < cutoff:
            try:
                log_path.unlink()
            except Exception:
                pass
    if ids_to_purge:
        with _db_connect() as con:
            con.executemany("DELETE FROM tasks WHERE task_id=?", [(i,) for i in ids_to_purge])
            con.commit()


def cleanup_caches(ttl_days: int):
    if ttl_days <= 0:
        return
    cutoff = time.time() - ttl_days * 86400
    # Select candidates
    with _db_connect() as con:
        cur = con.execute(
            "SELECT cache_key, basename, last_access, available FROM caches WHERE COALESCE(last_access, created) < ?",
            (cutoff,),
        )
        rows = cur.fetchall()
    for row in rows:
        key = row["cache_key"]
        available = int(row["available"] or 0)
        # Step 1: mark unavailable to avoid races
        try:
            _db_cache_mark_gone(key)
        except Exception:
            pass
        # Step 2: delete filesystem safely
        d = _cache_dir(key)
        try:
            if d.exists():
                shutil.rmtree(d, ignore_errors=True)
        except Exception:
            # leave row with available=0; future hits will recompute
            continue
        # Step 3: delete db row
        try:
            with _db_connect() as con:
                con.execute("DELETE FROM caches WHERE cache_key=?", (key,))
                con.commit()
        except Exception:
            # row remains with available=0; harmless for correctness
            pass


def start_cleanup_loop(task_retention_days: Optional[int], cache_ttl_days: Optional[int]):
    if task_retention_days is None and cache_ttl_days is None:
        return
    def loop():
        while True:
            try:
                if task_retention_days is not None:
                    cleanup_old_jobs(task_retention_days)
            except Exception:
                pass
            try:
                if cache_ttl_days is not None:
                    cleanup_caches(cache_ttl_days)
            except Exception:
                pass
            time.sleep(6 * 3600)
    t = threading.Thread(target=loop, name="cleanup-loop", daemon=True)
    t.start()


def _safe_filename_from_url(url: str) -> str:
    try:
        from urllib.parse import urlparse
        p = urlparse(url)
        name = Path(p.path).name
        if not name:
            return "document.docx"
        # ensure .docx suffix
        if not name.lower().endswith(".docx"):
            name = f"{name}.docx"
        return safe_name(name)
    except Exception:
        return "document.docx"


def process_job(task_id: str, source_kind: str, source_value: str, debug: bool, img_post_proc: bool, conf_file: Optional[Path], custom_xsl: Optional[Path]):
    js = jobs.get(task_id)
    work = Path(js.work_dir)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / f"{task_id}.log"

    # Determine original filename and derived paths
    if source_kind == "file":
        orig_name = Path(source_value).name
    else:
        orig_name = _safe_filename_from_url(source_value)
    orig_name = safe_name(orig_name or "document.docx")
    basename = Path(orig_name).stem

    out_tex = work / f"{basename}.tex"
    out_xml = work / f"{basename}.xml"
    debug_dir = work / f"{basename}.debug"
    result_zip = work / f"{basename}.zip"

    # Prepare input
    try:
        jobs.set_state(task_id, "running")
        input_docx = work / orig_name
        if source_kind == "file":
            # Already written by endpoint (to work/orig_name)
            if not input_docx.exists():
                # fallback: copy from provided path
                try:
                    data = Path(source_value).read_bytes()
                    write_bytes(input_docx, data)
                except Exception:
                    raise
        elif source_kind == "url":
            jobs.set_state(task_id, "running")
            download_to(input_docx, source_value)
        else:
            raise RuntimeError("invalid source kind")

        # Resolve configuration
        chosen_conf = conf_file if conf_file else DEFAULT_CONF

        # compute cache key from (docx, conf, xsl)
        cache_key = compute_cache_key(input_docx, chosen_conf, custom_xsl)
        _db_set_sha(task_id, cache_key)
        # console: initial cache status snapshot
        row0 = _db_cache_get(cache_key)
        if row0 and int(row0.get("available", 0)) == 1:
            _console(f"task={task_id} cache_status=HIT key={cache_key}")
        else:
            lk0 = _db_lock_get(cache_key)
            cs0 = "BUILDING" if lk0 else "MISS"
            _console(f"task={task_id} cache_status={cs0} key={cache_key}")

        reused = False
        # Quick READY hit
        row = _db_cache_get(cache_key)
        if row and int(row.get("available", 0)) == 1:
            cached_base = row.get("basename") or basename
            _log_line(log_path, f"cache_hit key={cache_key} cached_base={cached_base} -> restore to {basename}")
            _console(f"task={task_id} cache_hit key={cache_key}")
            try:
                _cache_restore(cache_key, cached_base, basename, Path(js.work_dir))
            except Exception as e:
                _log_exception(log_path, "cache_restore_error", e)
                cached_base = None
            if cached_base:
                _log_line(log_path, "cache_restore_done")
                _db_cache_touch(cache_key)
                reused = True
        elif not row or int(row.get("available", 0)) == 0:
            # Self-heal: if disk cache exists but DB row isn't READY, republish
            base_on_disk = _cache_disk_ok(cache_key)
            if base_on_disk:
                try:
                    _db_cache_put(cache_key, base_on_disk)
                    _console(f"task={task_id} cache_self_heal key={cache_key} base={base_on_disk}")
                    _log_line(log_path, f"cache_self_heal key={cache_key} base={base_on_disk}")
                    _db_cache_touch(cache_key)
                    cached_base = base_on_disk
                    try:
                        _cache_restore(cache_key, cached_base, basename, Path(js.work_dir))
                    except Exception as e:
                        _log_exception(log_path, "cache_restore_error", e)
                        cached_base = None
                    if cached_base:
                        _log_line(log_path, "cache_restore_done")
                        reused = True
                except Exception as e:
                    _log_exception(log_path, "cache_self_heal_failed", e)
            # only mark reused if we actually restored something
            if base_on_disk:
                _log_line(log_path, "cache_restore_done")
                _db_cache_touch(cache_key)
                reused = True
        else:
            # Try claim builder lock
            claimed = _db_lock_claim(cache_key, task_id)
            if not claimed:
                # Wait a short period for publish or lock release
                max_wait = float(os.environ.get("WAIT_PUBLISH_MAX_SEC", "3"))
                lock_max_age = int(os.environ.get("LOCK_MAX_AGE_SEC", "1800"))
                waited = 0.0
                _console(f"task={task_id} cache_building_wait key={cache_key}")
                while waited < max_wait:
                    row2 = _db_cache_get(cache_key)
                    if row2 and int(row2.get("available", 0)) == 1:
                        cached_base = row2.get("basename") or basename
                        _log_line(log_path, f"cache_hit_after_wait key={cache_key} cached_base={cached_base} -> restore to {basename}")
                        _console(f"task={task_id} cache_hit_after_wait key={cache_key}")
                        try:
                            _cache_restore(cache_key, cached_base, basename, Path(js.work_dir))
                        except Exception as e:
                            _log_exception(log_path, "cache_restore_error", e)
                            cached_base = None
                        _log_line(log_path, "cache_restore_done")
                        _db_cache_touch(cache_key)
                        reused = True
                        break
                    # Check lock expiry
                    lk = _db_lock_get(cache_key)
                    if lk and (time.time() - float(lk.get("started") or 0)) > lock_max_age:
                        _log_line(log_path, f"lock_expired key={cache_key}; reclaiming")
                        _console(f"task={task_id} lock_expired key={cache_key} reclaiming")
                        _db_lock_release(cache_key)
                        if _db_lock_claim(cache_key, task_id):
                            _console(f"task={task_id} lock_claimed key={cache_key}")
                            claimed = True
                            break
                    # Self-heal during wait as well
                    if not reused:
                        base_on_disk2 = _cache_disk_ok(cache_key)
                        if base_on_disk2:
                            try:
                                _db_cache_put(cache_key, base_on_disk2)
                                _console(f"task={task_id} cache_self_heal_wait key={cache_key} base={base_on_disk2}")
                                _db_cache_touch(cache_key)
                            except Exception as e:
                                _log_exception(log_path, "cache_self_heal_wait_failed", e)
                    time.sleep(0.5)
                    waited += 0.5
                if not reused and not claimed:
                    # Try final claim
                    claimed = _db_lock_claim(cache_key, task_id)
                    if claimed:
                        _console(f"task={task_id} lock_claimed key={cache_key}")

        # Build Calabash command
        if not reused:
            _log_line(log_path, f"cache_miss key={cache_key}; running docx2tex ...")
            _console(f"task={task_id} stage=docx2tex key={cache_key}")
            jobs.set_state(task_id, "converting")
            cmd = [
                str(CALABASH),
                "-o",
                f"result={to_file_uri(out_tex)}",
                "-o",
                f"hub={to_file_uri(out_xml)}",
                to_file_uri(DOCX2TEX_XPL),
                f"docx={to_file_uri(input_docx)}",
                f"conf={to_file_uri(chosen_conf)}",
                f"debug={'yes'}",
                f"debug-dir-uri={to_file_uri(debug_dir)}",
            ]
            if custom_xsl:
                cmd.append(f"custom-xsl={to_file_uri(custom_xsl)}")

            env = os.environ.copy()
            if CATALOG_FILE.exists():
                env["XML_CATALOG_FILES"] = str(CATALOG_FILE)

            rc, out, err = run_subprocess(cmd, env=env, timeout=900)
            # append docx2tex stdout/stderr to log; do not overwrite prior cache logs
            try:
                with open(log_path, "ab") as lf:
                    if out:
                        lf.write(out.encode("utf-8", errors="ignore"))
                    lf.write(b"\n--- STDERR ---\n")
                    if err:
                        lf.write(err.encode("utf-8", errors="ignore"))
            except Exception:
                pass
            if rc != 0 or not out_tex.exists():
                jobs.set_state(task_id, "failed", err or "docx2tex failed")
                _console(f"task={task_id} stage=docx2tex_failed")
                return

            # After successful parse, populate cache for this cache_key
            try:
                _cache_save(cache_key, basename, Path(js.work_dir))
                _db_cache_put(cache_key, basename)
                _log_line(log_path, f"cache_saved key={cache_key} base={basename}")
                _console(f"task={task_id} cache_saved key={cache_key}")
            except Exception as e:
                _log_exception(log_path, "cache_save_failed", e)
            finally:
                _db_lock_release(cache_key)

        # Vector images conversion
        if img_post_proc:
            _log_line(log_path, "image_post_proc=on")
            _console(f"task={task_id} stage=image_post_proc:on")
            jobs.set_state(task_id, "converting")
            conv_script = APP_HOME / "scripts" / "convert_vector_images.py"
            rc2, out2, err2 = run_subprocess(["python3", str(conv_script), str(out_tex)], timeout=600)
            with open(log_path, "ab") as lf:
                lf.write(b"\n--- convert_vector_images ---\n")
                lf.write((out2 or "").encode("utf-8") + b"\n" + (err2 or "").encode("utf-8"))
        else:
            _log_line(log_path, "image_post_proc=off")
            _console(f"task={task_id} stage=image_post_proc:off")

        # Packaging
        jobs.set_state(task_id, "packaging")
        # If debug off → pack only .tex + image/ (referenced images)
        if not debug:
            pack_script = APP_HOME / "scripts" / "pack_tex_with_images.py"
            rc3, out3, err3 = run_subprocess(["python3", str(pack_script), str(out_tex), "--image-dir", "image"], timeout=300)
            with open(log_path, "ab") as lf:
                lf.write(b"\n--- pack_tex_with_images ---\n")
                lf.write((out3 or "").encode("utf-8") + b"\n" + (err3 or "").encode("utf-8"))

        # Build manifest
        manifest = {
            "task_id": task_id,
            "debug": debug,
            "start_time": js.start_time,
            "end_time": time.time(),
            "files": [],
        }

        # Create ZIP
        from zipfile import ZipFile, ZIP_DEFLATED

        # Write ZIP to PUBLIC_ROOT
        PUBLIC_ROOT.mkdir(parents=True, exist_ok=True)
        result_zip_public = PUBLIC_ROOT / f"{basename}.zip"
        _log_line(log_path, f"packaging -> {result_zip_public}")
        _console(f"task={task_id} stage=packaging zip={result_zip_public}")
        with ZipFile(result_zip_public, "w", ZIP_DEFLATED) as zf:
            if debug:
                # 1) main outputs with original names
                for p in [out_tex, out_xml]:
                    if p.exists():
                        zf.write(p, arcname=p.name)
                        manifest["files"].append(p.name)
                # 2) generated CSV config (if present)
                csv_path = work / f"{basename}.csv"
                if csv_path.exists():
                    zf.write(csv_path, arcname=csv_path.name)
                    manifest["files"].append(csv_path.name)
                # 3) debug directory (basename.debug)
                if debug_dir.exists():
                    for sub in debug_dir.rglob("*"):
                        if sub.is_file():
                            arc = f"{debug_dir.name}/{sub.relative_to(debug_dir)}"
                            zf.write(sub, arcname=arc)
                            manifest["files"].append(arc)
                # 4) extracted resources folder (basename.docx.tmp)
                tmp_dir = work / f"{basename}.docx.tmp"
                if tmp_dir.exists():
                    for sub in tmp_dir.rglob("*"):
                        if sub.is_file():
                            arc = f"{tmp_dir.name}/{sub.relative_to(tmp_dir)}"
                            zf.write(sub, arcname=arc)
                            manifest["files"].append(arc)
                # 5) optional log
                if log_path.exists():
                    arc = f"logs/{log_path.name}"
                    zf.write(log_path, arcname=arc)
                    manifest["files"].append(arc)
            else:
                # minimal: out.tex + image/
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
            # manifest last
            zf.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))

        jobs.set_state(task_id, "done")
        _log_line(log_path, "task_done")
        _console(f"task={task_id} stage=done")
    except Exception as e:
        _log_line(log_path, f"task_failed: {e}")
        jobs.set_state(task_id, "failed", str(e))
        _console(f"task={task_id} stage=failed error={e}")


@app.post("/v1/task")
async def create_task(
    file: UploadFile | None = File(default=None),
    url: str | None = Form(default=None),
    debug: bool = Form(default=False),
    img_post_proc: bool = Form(default=True),
    conf: UploadFile | None = File(default=None),
    custom_xsl: UploadFile | None = File(default=None),
):
    if (file is None and not url) or (file is not None and url):
        raise HTTPException(status_code=400, detail="Provide exactly one of file or url")

    js = jobs.create(debug=debug, img_post_proc=img_post_proc)
    work = Path(js.work_dir)

    # Save input to work and compute cache_key for response
    if file is not None:
        name = safe_name(file.filename or "document.docx")
        if not name.lower().endswith(".docx"):
            name = f"{name}.docx"
        input_docx = work / name
        ctype = (file.content_type or "").lower()
        if ctype and "officedocument.wordprocessingml.document" not in ctype:
            pass
        await write_upload_stream(file, input_docx, MAX_UPLOAD_BYTES)
    else:
        # URL mode: download so we can compute cache_key for response
        name = _safe_filename_from_url(url or "")
        input_docx = work / name
        download_to(input_docx, url or "")

    conf_path: Optional[Path] = None
    if conf is not None:
        conf_path = work / "conf.xml"
        write_bytes(conf_path, await conf.read())
        # Normalize <import href="conf.xml"/> to absolute default conf inside container
        try:
            _maybe_rewrite_conf_imports(conf_path)
        except Exception:
            pass

    xsl_path: Optional[Path] = None
    if custom_xsl is not None:
        xsl_path = work / "custom.xsl"
        write_bytes(xsl_path, await custom_xsl.read())

    # Compute cache key for response
    chosen_conf = conf_path if conf_path else DEFAULT_CONF
    try:
        cache_key = compute_cache_key(input_docx, chosen_conf, xsl_path)
        row = _db_cache_get(cache_key)
        if row and int(row.get("available", 0)) == 1:
            cache_status = "HIT"
        else:
            lk = _db_lock_get(cache_key)
            cache_status = "BUILDING" if lk else "MISS"
    except Exception:
        cache_key = None
        cache_status = "N/A"

    # Submit background job (already saved the input path; mark kind=file for both)
    source_kind = "file"
    source_value = str(input_docx)
    jobs.pool.submit(process_job, js.task_id, source_kind, source_value, debug, img_post_proc, conf_path, xsl_path)

    return JSONResponse({"task_id": js.task_id, "cache_key": cache_key, "cache_status": cache_status})


@app.get("/v1/task/{task_id}")
def get_status(task_id: str):
    try:
        js = jobs.get(task_id)
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


@app.get("/v1/task/{task_id}/result")
def get_result(task_id: str):
    try:
        js = jobs.get(task_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="task not found")
    if js.state != "done":
        raise HTTPException(status_code=409, detail=f"task state: {js.state}")
    work = Path(js.work_dir)
    # infer basename from any .tex present
    tex_files = list(work.glob("*.tex"))
    basename = tex_files[0].stem if tex_files else Path(work).name
    zf = PUBLIC_ROOT / f"{basename}.zip"
    if not zf.exists():
        raise HTTPException(status_code=500, detail="result missing")
    return StreamingResponse(open(zf, "rb"), media_type="application/zip", headers={"Content-Disposition": f"attachment; filename={basename}.zip"})


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/version")
def version():
    return {
        "service": "docx2tex-service",
        "docx2tex_home": str(DOCX2TEX_HOME),
    }


@app.on_event("startup")
def on_startup():
    # Ensure dirs (DATA_ROOT private; PUBLIC_ROOT is user-visible)
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    PUBLIC_ROOT.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    _db_init()
    # Determine unified TTL (days) for tasks and caches
    env_days = os.environ.get("TTL_DAYS", "").strip()
    retention: Optional[int]
    if env_days:
        try:
            retention = int(env_days)
        except ValueError:
            retention = 7
    else:
        if is_mountpoint(DATA_ROOT):
            retention = None  # mounted: if unset, do not clean
        else:
            retention = 7
    start_cleanup_loop(retention, retention)
    # Start high-frequency lock sweeper
    sweep_int = int(os.environ.get("LOCK_SWEEP_INTERVAL_SEC", "120"))
    lock_max  = int(os.environ.get("LOCK_MAX_AGE_SEC", "1800"))
    start_lock_sweeper(sweep_int, lock_max)
