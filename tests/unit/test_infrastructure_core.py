from __future__ import annotations

import json
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from document_conversion.infrastructure.cache import CacheStore, LockManager
from document_conversion.infrastructure.config import Config
from document_conversion.infrastructure.database import Database
from document_conversion.infrastructure.state import JobState, TaskStore
from document_conversion.infrastructure.storage import atomic_write_json, compute_sha256, safe_name
from engines.docx2tex_engine.assets import resolve_docx2tex_home
from engines.docx2tex_engine.convert import compute_cache_key, rewrite_conf_imports_to_default
from engines.docx2tex_engine.filenames import (
    INTERNAL_BASENAME,
    INTERNAL_DOCX_FILENAME,
    name_mapping_from_upload,
    name_mapping_from_url,
)


def test_config_from_env_defaults():
    cfg = Config.from_env()
    assert cfg.data_root
    assert cfg.public_root
    assert cfg.log_dir


def test_storage_helpers_and_filename_metadata(report_results):
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "data.json"
        atomic_write_json(path, {"x": 1})
        assert json.loads(path.read_text(encoding="utf-8")) == {"x": 1}
        assert len(compute_sha256(path)) == 64
    assert safe_name("a b@c.txt") == "a_b_c.txt"
    upload_mapping = name_mapping_from_upload("安全报告.docx")
    report_results.append(
        ("Canonical docx2tex name", "安全报告.docx", upload_mapping.internal_filename)
    )
    assert upload_mapping.original_filename == "安全报告.docx"
    assert upload_mapping.display_basename == "安全报告"
    assert upload_mapping.internal_filename == INTERNAL_DOCX_FILENAME
    assert upload_mapping.internal_basename == INTERNAL_BASENAME
    assert upload_mapping.result_name == "安全报告.zip"

    url_mapping = name_mapping_from_url("https://example.test/files/../中文 报告")
    assert url_mapping.original_filename == "中文 报告.docx"
    assert url_mapping.display_basename == "中文 报告"


def test_cache_and_lock_roundtrip():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        db = Database(root / "state.db")
        db.init_schema()
        cache = CacheStore(db, root)
        key = "k1"
        assert cache.get(key) is None
        assert cache.reserve(key)
        cache.publish(key, "base")
        work = root / "work"
        (work / "base.debug").mkdir(parents=True, exist_ok=True)
        (work / "base.docx.tmp").mkdir(parents=True, exist_ok=True)
        (work / "base.tex").write_text("\\documentclass{article}", encoding="utf-8")
        (work / "base.xml").write_text("<hub/>", encoding="utf-8")
        cache.save_to_disk(key, "base", work)
        assert cache.disk_ok(key) == "base"
        dest = root / "dest"
        dest.mkdir(parents=True, exist_ok=True)
        cache.restore_to_work(key, "base", "newbase", dest)
        assert (dest / "newbase.tex").exists()

        locks = LockManager(db)
        assert locks.claim("cache-key", "builder-1")
        assert not locks.claim("cache-key", "builder-2")
        locks.release("cache-key")


def test_task_store_and_convert_helpers():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        db = Database(root / "state.db")
        db.init_schema()
        store = TaskStore(db)
        state = JobState(
            task_id="t1",
            state="pending",
            start_time=time.time(),
            work_dir=str(root / "tasks" / "t1"),
        )
        store.insert(state)
        store.set_state("t1", "done")
        assert store.get("t1").state == "done"

        docx = root / "a.docx"
        conf = root / "conf.xml"
        xsl = root / "custom.xsl"
        docx.write_bytes(b"DOCX-A")
        conf.write_text("<c>A</c>", encoding="utf-8")
        xsl.write_text("<xsl/>", encoding="utf-8")
        key1 = compute_cache_key(docx, conf, xsl, None, "ole", "tabularx", None)
        conf.write_text("<c>B</c>", encoding="utf-8")
        key2 = compute_cache_key(docx, conf, xsl, None, "ole", "tabularx", None)
        assert key1 != key2

        imported_conf = root / "overlay.xml"
        imported_conf.write_text(
            "<set xmlns='http://transpect.io/xml2tex'><import href='conf.xml'/></set>",
            encoding="utf-8",
        )
        assert rewrite_conf_imports_to_default(imported_conf, conf)


def test_docx2tex_upstream_xproc_ports_are_aligned():
    ns = {"p": "http://www.w3.org/ns/xproc"}
    docx2tex_home = resolve_docx2tex_home()
    docx2tex_xpl = docx2tex_home / "xpl" / "docx2tex.xpl"
    xml2tex_xpl = docx2tex_home / "xml2tex" / "xpl" / "xml2tex.xpl"

    docx2tex_tree = ET.parse(docx2tex_xpl)
    xml2tex_tree = ET.parse(xml2tex_xpl)

    referenced_ports = {
        pipe.attrib["port"]
        for pipe in docx2tex_tree.findall(".//p:pipe[@step='xml2tex']", ns)
        if pipe.attrib.get("port")
    }
    declared_ports = {
        output.attrib["port"]
        for output in xml2tex_tree.findall("./p:output", ns)
        if output.attrib.get("port")
    }

    assert referenced_ports <= declared_ports, (
        "docx2tex.xpl references xml2tex output ports that xml2tex.xpl does not expose: "
        f"{sorted(referenced_ports - declared_ports)}"
    )
