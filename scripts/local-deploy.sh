#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"
RELOAD="${RELOAD:-0}"

usage() {
  cat <<'EOF'
Usage:
  bash scripts/local-deploy.sh check
  bash scripts/local-deploy.sh serve [--reload] [--host HOST] [--port PORT]

Behavior:
  - exports repository-local runtime paths
  - uses the currently active Python environment
  - runs system checks before starting the service
EOF
}

run_cli() {
  python -u -m document_conversion.interfaces.cli "$@"
}

export_runtime_env() {
  export PYTHONPATH="${ROOT_DIR}/src:${ROOT_DIR}"
  export DATA_ROOT="${DATA_ROOT:-${ROOT_DIR}/.local/data}"
  export WORK_ROOT="${WORK_ROOT:-${ROOT_DIR}/.local/work}"
  export LOG_DIR="${LOG_DIR:-${ROOT_DIR}/.local/logs}"
  export DOCX2TEX_HOME="${DOCX2TEX_HOME:-${ROOT_DIR}/src/engines/docx2tex_engine/vendor/docx2tex}"
  export XML_CATALOG_FILES="${XML_CATALOG_FILES:-}"
  export PORT

  mkdir -p "$DATA_ROOT" "$WORK_ROOT" "$LOG_DIR"
}

print_summary() {
  cat <<EOF
[local-deploy] ROOT_DIR=${ROOT_DIR}
[local-deploy] DATA_ROOT=${DATA_ROOT}
[local-deploy] WORK_ROOT=${WORK_ROOT}
[local-deploy] LOG_DIR=${LOG_DIR}
[local-deploy] DOCX2TEX_HOME=${DOCX2TEX_HOME}
[local-deploy] XML_CATALOG_FILES=${XML_CATALOG_FILES}
[local-deploy] HOST=${HOST}
[local-deploy] PORT=${PORT}
EOF
}

parse_serve_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --reload)
        RELOAD=1
        shift
        ;;
      --host)
        HOST="$2"
        shift 2
        ;;
      --port)
        PORT="$2"
        shift 2
        ;;
      *)
        echo "Unknown option: $1" >&2
        usage
        exit 2
        ;;
    esac
  done
}

main() {
  if [[ $# -lt 1 ]]; then
    usage
    exit 2
  fi

  local command="$1"
  shift

  export_runtime_env

  case "$command" in
    check)
      print_summary
      run_cli check-system
      ;;
    serve)
      parse_serve_args "$@"
      export HOST PORT
      print_summary
      run_cli check-system
      if [[ "$RELOAD" == "1" ]]; then
        run_cli serve --reload
        exit $?
      fi
      run_cli serve
      exit $?
      ;;
    *)
      echo "Unknown command: $command" >&2
      usage
      exit 2
      ;;
  esac
}

main "$@"
