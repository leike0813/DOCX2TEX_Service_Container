from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from .db import Database
from .models import JobState


@dataclass
class TaskStore:
    db: Database

    def insert(self, js: JobState) -> None:
        with self.db.connect() as con:
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

    def get(self, task_id: str) -> JobState:
        with self.db.connect() as con:
            cur = con.execute("SELECT * FROM tasks WHERE task_id=?", (task_id,))
            row = cur.fetchone()
            if not row:
                raise KeyError(task_id)
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

    def set_state(self, task_id: str, state: str, err: str = "") -> None:
        with self.db.connect() as con:
            end_time = time.time() if state in ("done", "failed") else None
            if end_time is None:
                con.execute("UPDATE tasks SET state=?, err_msg=? WHERE task_id=?", (state, err, task_id))
            else:
                con.execute("UPDATE tasks SET state=?, err_msg=?, end_time=? WHERE task_id=?", (state, err, end_time, task_id))
            con.commit()

    def set_sha256(self, task_id: str, sha: str) -> None:
        with self.db.connect() as con:
            con.execute("UPDATE tasks SET sha256=? WHERE task_id=?", (sha, task_id))
            con.commit()

