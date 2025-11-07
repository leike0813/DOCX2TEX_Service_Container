#!/usr/bin/env bash
set -euo pipefail

export APP_HOME="${APP_HOME:-/svc/app}"
export WORK_ROOT="${WORK_ROOT:-/work}"
export LOG_DIR="${LOG_DIR:-/var/log/docx2tex}"
export DOCX2TEX_HOME="${DOCX2TEX_HOME:-/opt/docx2tex}"

mkdir -p "$WORK_ROOT" "$LOG_DIR"

echo "[entrypoint] APP_HOME=$APP_HOME WORK_ROOT=$WORK_ROOT LOG_DIR=$LOG_DIR DOCX2TEX_HOME=$DOCX2TEX_HOME"

UVICORN_BIN="/opt/venv/bin/uvicorn"
APP_IMPORT="app.server:app"  # use package import path
# Default to 2 workers now that job state is file-backed
WORKERS="${UVICORN_WORKERS:-2}"
if [ -x "$UVICORN_BIN" ]; then
  exec "$UVICORN_BIN" "$APP_IMPORT" --host 0.0.0.0 --port 8000 --workers "$WORKERS"
else
  exec uvicorn "$APP_IMPORT" --host 0.0.0.0 --port 8000 --workers "$WORKERS"
fi
