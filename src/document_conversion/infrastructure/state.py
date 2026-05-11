from __future__ import annotations

import time
from dataclasses import dataclass

from pydantic import BaseModel

from .database import Database


class JobState(BaseModel):
    task_id: str
    state: str
    err_msg: str = ""
    start_time: float
    end_time: float | None = None
    debug: bool = False
    img_post_proc: bool = True
    work_dir: str
    sha256: str | None = None


@dataclass
class TaskStore:
    db: Database

    def insert(self, job_state: JobState) -> None:
        with self.db.connect() as connection:
            connection.execute(
                (
                    "INSERT INTO tasks(task_id,state,err_msg,start_time,end_time,debug,"
                    "img_post_proc,work_dir,created,sha256) VALUES(?,?,?,?,?,?,?,?,?,?)"
                ),
                (
                    job_state.task_id,
                    job_state.state,
                    job_state.err_msg,
                    job_state.start_time,
                    job_state.end_time,
                    1 if job_state.debug else 0,
                    1 if job_state.img_post_proc else 0,
                    job_state.work_dir,
                    time.time(),
                    job_state.sha256,
                ),
            )
            connection.commit()

    def get(self, task_id: str) -> JobState:
        with self.db.connect() as connection:
            row = connection.execute("SELECT * FROM tasks WHERE task_id=?", (task_id,)).fetchone()
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
            sha256=row["sha256"],
        )

    def set_state(self, task_id: str, state: str, err: str = "") -> None:
        with self.db.connect() as connection:
            end_time = time.time() if state in {"done", "failed"} else None
            if end_time is None:
                connection.execute(
                    "UPDATE tasks SET state=?, err_msg=? WHERE task_id=?",
                    (state, err, task_id),
                )
            else:
                connection.execute(
                    "UPDATE tasks SET state=?, err_msg=?, end_time=? WHERE task_id=?",
                    (state, err, end_time, task_id),
                )
            connection.commit()

    def set_sha256(self, task_id: str, sha256: str) -> None:
        with self.db.connect() as connection:
            connection.execute("UPDATE tasks SET sha256=? WHERE task_id=?", (sha256, task_id))
            connection.commit()
