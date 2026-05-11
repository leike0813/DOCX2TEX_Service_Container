#!/usr/bin/env bash
set -euo pipefail

export WORK_ROOT="${WORK_ROOT:-/work}"
export LOG_DIR="${LOG_DIR:-/var/log/docx2tex}"
export DOCX2TEX_HOME="${DOCX2TEX_HOME:-/opt/docx2tex}"
export XML_CATALOG_FILES="${XML_CATALOG_FILES:-}"

mkdir -p "$WORK_ROOT" "$LOG_DIR"

PYTHON_BIN="${PYTHON_BIN:-/opt/venv/bin/python}"
UVICORN_BIN="${UVICORN_BIN:-/opt/venv/bin/uvicorn}"
APP_IMPORT="document_conversion.interfaces.api.app:app"
WORKERS="${UVICORN_WORKERS:-2}"

if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="$(command -v python)"
fi

if [ -x "$UVICORN_BIN" ]; then
  "$PYTHON_BIN" -u -m document_conversion.interfaces.cli check-system
  exec "$UVICORN_BIN" "$APP_IMPORT" --host 0.0.0.0 --port 8000 --workers "$WORKERS"
fi

"$PYTHON_BIN" -u -m document_conversion.interfaces.cli check-system
exec uvicorn "$APP_IMPORT" --host 0.0.0.0 --port 8000 --workers "$WORKERS"
