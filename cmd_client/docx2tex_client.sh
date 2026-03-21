#!/usr/bin/env bash
# Bash client for docx2tex service, mirroring cmd_client/docx2tex_client.ps1.
# Dependencies: curl, jq

set -euo pipefail

VERBOSE=0
CURL_VERBOSE=()

usage() {
  cat <<'EOF'
Usage:
  docx2tex_client.sh [task] --server URL (--file PATH.docx | --url DOCX_URL) [options]
  docx2tex_client.sh dryrun   --server URL [options]

Task options:
  --out FILE               Output ZIP (default: result_<8hex>.zip in CWD)
  --include-debug          Include debug output (default: false)
  --img-post-proc          Enable image post-process (default: true)
  --conf PATH              XML conf file
  --custom-xsl PATH        Custom XSL file
  --custom-evolve PATH     Custom evolve XML
  --stylemap STRING        StyleMap string value
  --mathtypesource STRING  MathTypeSource value
  --tablemodel STRING      TableModel value
  --fontmapszip PATH       FontMapsZip .zip file
  --image-dir STRING       image_dir value
  --no-cache               Use /v1/nocache instead of /v1/task
  --poll-interval SEC      Poll interval (default: 2)
  --timeout SEC            Task timeout seconds (default: 900)
  --verbose                Enable verbose logging (curl -v and debug output)

Dryrun options:
  --conf PATH              XML conf file
  --custom-evolve PATH     Custom evolve XML
  --stylemap STRING        StyleMap string value
  --out FILE               Output ZIP (default: dryrun_<8hex>.zip in CWD)
  --timeout SEC            Request timeout seconds (default: 300)
  --verbose                Enable verbose logging (curl -v and debug output)
EOF
}

die() { echo "Error: $*" >&2; exit 1; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Missing dependency: $1"
}

uuid8() {
  if command -v uuidgen >/dev/null 2>&1; then
    uuidgen | tr 'A-F' 'a-f' | tr -d '-' | cut -c1-8
  else
    # Fallback: date+pid hash
    printf '%08x' "$(($(date +%s) ^ $$))"
  fi
}

urlencode() {
  # Minimal urlencode for query/path fragments if needed later.
  python - <<'PY' "$1"
import sys, urllib.parse
print(urllib.parse.quote(sys.argv[1]))
PY
}

log_debug() {
  if [[ "${VERBOSE:-0}" == "1" ]]; then
    echo "[DEBUG] $*" >&2
  fi
}

sync_curl_verbose() {
  if [[ "${VERBOSE:-0}" == "1" ]]; then
    CURL_VERBOSE=(-v)
  else
    CURL_VERBOSE=()
  fi
}

assert_json() {
  local body=$1
  if ! printf '%s' "$body" | jq -e . >/dev/null 2>&1; then
    die "Non-JSON response: $body"
  fi
}

check_docx() {
  local f=$1
  [[ -f "$f" ]] || die "File not found: $f"
  [[ "${f,,}" == *.docx ]] || die "Only .docx is supported: $f"
}

make_out_path() {
  local path=$1
  local dir
  dir=$(dirname "$path")
  if [[ -n "$dir" && "$dir" != "." ]]; then
    mkdir -p "$dir"
  fi
}

post_task() {
  local server=$1 file=$2 url=$3 include_debug=$4 img_post_proc=$5 conf=$6 custom_xsl=$7 custom_evolve=$8 stylemap=$9 mathtypesource=${10} tablemodel=${11} fontmapszip=${12} image_dir=${13} no_cache=${14} timeout=${15}

  local endpoint
  if [[ "$no_cache" == "true" ]]; then
    endpoint="$server/v1/nocache"
  else
    endpoint="$server/v1/task"
  fi

  local -a form_args=()
  if [[ -n "$file" ]]; then
    form_args+=(-F "file=@${file};type=application/vnd.openxmlformats-officedocument.wordprocessingml.document")
  else
    form_args+=(-F "url=${url}")
  fi
  form_args+=(-F "debug=${include_debug}")
  form_args+=(-F "img_post_proc=${img_post_proc}")
  [[ -n "$conf" ]] && form_args+=(-F "conf=@${conf};type=application/xml")
  [[ -n "$custom_xsl" ]] && form_args+=(-F "custom_xsl=@${custom_xsl};type=application/xml")
  [[ -n "$custom_evolve" ]] && form_args+=(-F "custom_evolve=@${custom_evolve};type=application/xml")
  [[ -n "$stylemap" ]] && form_args+=(-F "StyleMap=${stylemap}")
  [[ -n "$mathtypesource" ]] && form_args+=(-F "MathTypeSource=${mathtypesource}")
  [[ -n "$tablemodel" ]] && form_args+=(-F "TableModel=${tablemodel}")
  [[ -n "$fontmapszip" ]] && form_args+=(-F "FontMapsZip=@${fontmapszip};type=application/zip")
  [[ -n "$image_dir" ]] && form_args+=(-F "image_dir=${image_dir}")

  local tmp http_code body
  tmp=$(mktemp)
  http_code=$(curl -sS "${CURL_VERBOSE[@]}" -w '%{http_code}' --output "$tmp" --max-time "$timeout" -X POST "${form_args[@]}" "$endpoint")
  body=$(cat "$tmp")
  rm -f "$tmp"
  log_debug "POST $endpoint code=$http_code body=$body"
  if [[ "$http_code" != 200 ]]; then
    die "HTTP $http_code $body"
  fi
  assert_json "$body"
  echo "$body"
}

get_task_status() {
  local server=$1 task_id=$2 timeout=$3
  local tmp http_code body
  tmp=$(mktemp)
  http_code=$(curl -sS "${CURL_VERBOSE[@]}" -w '%{http_code}' --output "$tmp" --max-time "$timeout" "$server/v1/task/$task_id")
  body=$(cat "$tmp")
  rm -f "$tmp"
  log_debug "GET $server/v1/task/$task_id code=$http_code body=$body"
  if [[ "$http_code" != 200 ]]; then
    die "HTTP $http_code $body"
  fi
  assert_json "$body"
  echo "$body"
}

download_result() {
  local server=$1 task_id=$2 outfile=$3 timeout=$4
  make_out_path "$outfile"
  # Need to inspect status code for 409
  local tmp
  tmp=$(mktemp)
  http_code=$(curl -sS "${CURL_VERBOSE[@]}" -w '%{http_code}' --output "$tmp" --max-time "$timeout" "$server/v1/task/$task_id/result")
  log_debug "GET $server/v1/task/$task_id/result code=$http_code (saved to $tmp)"
  if [[ "$http_code" == "409" ]]; then
    local msg
    msg=$(cat "$tmp")
    rm -f "$tmp"
    die "Task not ready (409): $msg"
  fi
  if [[ "$http_code" != "200" ]]; then
    local msg
    msg=$(cat "$tmp")
    rm -f "$tmp"
    die "HTTP $http_code $msg"
  fi
  mv "$tmp" "$outfile"
  echo "$outfile"
}

poll_task() {
  local server=$1 task_id=$2 poll_interval=$3 timeout=$4
  local start
  start=$(date +%s)
  while true; do
    local resp state now
    resp=$(get_task_status "$server" "$task_id" "$timeout")
    state=$(echo "$resp" | jq -r '.data.state')
    now=$(date)
    echo "[$now] state=${state}" >&2
    if [[ "$state" == "done" || "$state" == "failed" ]]; then
      echo "$resp"
      return 0
    fi
    sleep "$poll_interval"
    local now_ts
    now_ts=$(date +%s)
    if (( now_ts - start > timeout )); then
      die "Timeout waiting for task $task_id"
    fi
  done
}

handle_task() {
  local server file url outfile include_debug img_post_proc conf custom_xsl custom_evolve stylemap mathtypesource tablemodel fontmapszip image_dir no_cache poll_interval timeout
  server="" file="" url="" outfile="" include_debug="false" img_post_proc="true" conf="" custom_xsl="" custom_evolve="" stylemap="" mathtypesource="" tablemodel="" fontmapszip="" image_dir="" no_cache="false" poll_interval=2 timeout=900

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --server) server=$2; shift 2 ;;
      --file) file=$2; shift 2 ;;
      --url) url=$2; shift 2 ;;
      --out) outfile=$2; shift 2 ;;
      --include-debug) include_debug="true"; shift 1 ;;
      --img-post-proc) img_post_proc="true"; shift 1 ;;
      --no-img-post-proc) img_post_proc="false"; shift 1 ;;
      --conf) conf=$2; shift 2 ;;
      --custom-xsl) custom_xsl=$2; shift 2 ;;
      --custom-evolve) custom_evolve=$2; shift 2 ;;
      --stylemap) stylemap=$2; shift 2 ;;
      --mathtypesource) mathtypesource=$2; shift 2 ;;
      --tablemodel) tablemodel=$2; shift 2 ;;
      --fontmapszip) fontmapszip=$2; shift 2 ;;
      --image-dir) image_dir=$2; shift 2 ;;
      --no-cache) no_cache="true"; shift 1 ;;
      --poll-interval) poll_interval=$2; shift 2 ;;
      --timeout) timeout=$2; shift 2 ;;
      --verbose) VERBOSE=1; shift 1 ;;
      -h|--help) usage; exit 0 ;;
      *) die "Unknown option: $1" ;;
    esac
  done

  [[ -n "$server" ]] || die "--server is required"
  if [[ -n "$file" && -n "$url" ]]; then
    die "--file and --url are mutually exclusive"
  fi
  if [[ -z "$file" && -z "$url" ]]; then
    die "One of --file or --url is required"
  fi
  if [[ -n "$file" ]]; then
    check_docx "$file"
  fi
  [[ -n "$conf" && ! -f "$conf" ]] && die "Conf not found: $conf"
  [[ -n "$custom_xsl" && ! -f "$custom_xsl" ]] && die "CustomXsl not found: $custom_xsl"
  [[ -n "$custom_evolve" && ! -f "$custom_evolve" ]] && die "CustomEvolve not found: $custom_evolve"
  [[ -n "$fontmapszip" && ! -f "$fontmapszip" ]] && die "FontMapsZip not found: $fontmapszip"

  if [[ -z "$outfile" ]]; then
    outfile="result_$(uuid8).zip"
  fi

  echo "Submitting task..."
  sync_curl_verbose
  local resp
  resp=$(post_task "$server" "$file" "$url" "$include_debug" "$img_post_proc" "$conf" "$custom_xsl" "$custom_evolve" "$stylemap" "$mathtypesource" "$tablemodel" "$fontmapszip" "$image_dir" "$no_cache" "$timeout")

  local task_id cache_key cache_status cache_hit
  task_id=$(echo "$resp" | jq -r '.task_id // .data.task_id // empty')
  [[ -n "$task_id" ]] || die "Task id missing in response: $resp"
  cache_key=$(echo "$resp" | jq -r '.cache_key // empty')
  cache_hit=$(echo "$resp" | jq -r 'if has("cache_hit") then .cache_hit else empty end')
  cache_status=$(echo "$resp" | jq -r '.cache_status // empty')
  if [[ -z "$cache_status" ]]; then
    if [[ "$cache_hit" == "true" ]]; then
      cache_status="HIT"
    elif [[ "$cache_hit" == "false" && -n "$cache_key" ]]; then
      cache_status="MISS/BUILDING"
    else
      cache_status="N/A"
    fi
  fi
  echo "cache_key=${cache_key:-} cache_status=${cache_status}"

  local st
  st=$(poll_task "$server" "$task_id" "$poll_interval" "$timeout")
  state=$(echo "$st" | jq -r '.data.state')
  if [[ "$state" != "done" ]]; then
    err_msg=$(echo "$st" | jq -r '.data.err_msg // "unknown error"')
    die "Task failed: $err_msg"
  fi

  local zip_path
  zip_path=$(download_result "$server" "$task_id" "$outfile" "$timeout")
  zip_path=$(cd "$(dirname "$zip_path")" && pwd)/$(basename "$zip_path")

  jq -n --arg task_id "$task_id" --arg cache_key "${cache_key:-}" --arg cache_status "$cache_status" --arg state "$state" --arg zip "$zip_path" '{TaskId:$task_id, CacheKey:$cache_key, CacheStatus:$cache_status, State:$state, Zip:$zip}'
}

handle_dryrun() {
  local server conf custom_evolve stylemap outfile timeout
  server="" conf="" custom_evolve="" stylemap="" outfile="" timeout=300

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --server) server=$2; shift 2 ;;
      --conf) conf=$2; shift 2 ;;
      --custom-evolve) custom_evolve=$2; shift 2 ;;
      --stylemap) stylemap=$2; shift 2 ;;
      --out) outfile=$2; shift 2 ;;
      --timeout) timeout=$2; shift 2 ;;
      --verbose) VERBOSE=1; shift 1 ;;
      -h|--help) usage; exit 0 ;;
      *) die "Unknown option: $1" ;;
    esac
  done

  [[ -n "$server" ]] || die "--server is required"
  [[ -n "$conf" && ! -f "$conf" ]] && die "Conf not found: $conf"
  [[ -n "$custom_evolve" && ! -f "$custom_evolve" ]] && die "CustomEvolve not found: $custom_evolve"

  if [[ -z "$outfile" ]]; then
    outfile="dryrun_$(uuid8).zip"
  fi

  make_out_path "$outfile"
  sync_curl_verbose
  local -a form_args=()
  [[ -n "$conf" ]] && form_args+=(-F "conf=@${conf};type=application/xml")
  [[ -n "$custom_evolve" ]] && form_args+=(-F "custom_evolve=@${custom_evolve};type=application/xml")
  [[ -n "$stylemap" ]] && form_args+=(-F "StyleMap=${stylemap}")

  local tmp http_code
  tmp=$(mktemp)
  http_code=$(curl -sS -w '%{http_code}' --output "$tmp" --max-time "$timeout" -X POST "${form_args[@]}" "$server/v1/dryrun")
  if [[ "$http_code" != "200" ]]; then
    local msg
    msg=$(cat "$tmp")
    rm -f "$tmp"
    die "HTTP $http_code $msg"
  fi
  mv "$tmp" "$outfile"
  echo "DryRun ZIP -> $(cd "$(dirname "$outfile")" && pwd)/$(basename "$outfile")"
}

main() {
  require_cmd curl
  require_cmd jq
  if [[ $# -eq 0 ]]; then
    usage; exit 1
  fi
  local sub=$1; shift || true
  case "$sub" in
    dryrun) handle_dryrun "$@" ;;
    task|--*|*) handle_task "$sub" "$@" ;; # default subcommand is task; pass back first token if it's an option
  esac
}

main "$@"
