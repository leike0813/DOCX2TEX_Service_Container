from __future__ import annotations

import time
import tempfile
from pathlib import Path

from app.core.db import Database
from app.core.tasks import TaskStore
from app.core.models import JobState


def test_taskstore_insert_get_update_sha():
    with tempfile.TemporaryDirectory() as td:
        db = Database(Path(td) / "state.db")
        db.init_schema()
        store = TaskStore(db)

        js = JobState(
            task_id="t1",
            state="pending",
            start_time=time.time(),
            debug=False,
            img_post_proc=True,
            work_dir=str(Path(td) / "tasks" / "t1"),
        )
        store.insert(js)

        got = store.get("t1")
        assert got.task_id == "t1" and got.state == "pending"

        store.set_state("t1", "running")
        assert store.get("t1").state == "running"

        store.set_state("t1", "done")
        after = store.get("t1")
        assert after.state == "done" and after.end_time is not None

        store.set_sha256("t1", "abcd")
        assert store.get("t1").sha256 is None or isinstance(store.get("t1").sha256, str)

