#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"
COMMAND="${1:-help}"
shift || true
PID_FILE="$ROOT_DIR/run/server.pid"
LOG_DIR="$ROOT_DIR/logs"
HOST_VALUE=""
PORT_VALUE=""
LABEL="user1"
FORCE="false"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --host|-Host|-ListenHost)
      HOST_VALUE="${2:?missing host}"; shift 2 ;;
    --port|-Port)
      PORT_VALUE="${2:?missing port}"; shift 2 ;;
    --label|-Label)
      LABEL="${2:?missing label}"; shift 2 ;;
    --force|-Force)
      FORCE="true"; shift ;;
    *)
      echo "Unknown option: $1" >&2; exit 2 ;;
  esac
done

help() {
  cat <<'HELP'
Vox Local Story TTS - Linux deploy CLI

Usage:
  ./vox.sh setup                 Create venv, install deps, setup CapCut provider
  ./vox.sh install               Create venv, install deps, copy .env if missing
  ./vox.sh setup-capcut          Clone/update K07VN/capcut-tts-api and update .env
  ./vox.sh run                   Run server foreground
  ./vox.sh start                 Start server in background
  ./vox.sh stop                  Stop background server
  ./vox.sh status                Show PID and port listener status
  ./vox.sh key --label pc-main   Generate API key and SHA-256 hash
  ./vox.sh clean-deploy          Dry-run local artifact cleanup
  ./vox.sh clean-deploy --force  Clean local artifacts, keep source and device JSON

Options:
  --host 127.0.0.1
  --port 8010
HELP
}

ensure_dirs() {
  mkdir -p providers audio_cache logs run
}

copy_env_if_missing() {
  if [[ ! -f .env ]]; then
    if [[ -f .env.example ]]; then cp .env.example .env; else touch .env; fi
  fi
}

python_bin() {
  if [[ -x .venv/bin/python ]]; then echo ".venv/bin/python"; else echo "python3"; fi
}

set_env_value() {
  local name="$1" value="$2"
  touch .env
  if grep -qE "^[[:space:]]*${name}=" .env; then
    python3 - "$name" "$value" <<'PY'
from pathlib import Path
import sys
name, value = sys.argv[1], sys.argv[2]
path = Path('.env')
lines = path.read_text(encoding='utf-8').splitlines()
out = [f'{name}={value}' if line.lstrip().startswith(f'{name}=') else line for line in lines]
path.write_text('\n'.join(out) + '\n', encoding='utf-8')
PY
  else
    printf '%s=%s\n' "$name" "$value" >> .env
  fi
}

install_deps() {
  ensure_dirs
  copy_env_if_missing
  if [[ ! -x .venv/bin/python ]]; then
    python3 -m venv .venv
  fi
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -r requirements.txt
}

setup_capcut() {
  ensure_dirs
  copy_env_if_missing
  if ! command -v git >/dev/null 2>&1; then echo "git is required" >&2; exit 1; fi
  if [[ -d providers/capcut-tts-api/.git ]]; then
    git -C providers/capcut-tts-api pull --ff-only
  elif [[ -f providers/capcut-tts-api/capcut_common_task_client.py ]]; then
    echo "Using existing providers/capcut-tts-api"
  else
    rm -rf providers/capcut-tts-api
    git clone --depth 1 https://github.com/K07VN/capcut-tts-api.git providers/capcut-tts-api
  fi
  .venv/bin/python -m pip install requests
  set_env_value TTS_PROVIDER capcut
  set_env_value ALLOW_NETWORK_TTS true
  set_env_value TTS_FALLBACK_TO_LOCAL false
  set_env_value CAPCUT_CLIENT_PATH providers/capcut-tts-api/capcut_common_task_client.py
  set_env_value CAPCUT_PYTHON .venv/bin/python
  if [[ -f capcut_device_windows.json ]]; then
    set_env_value CAPCUT_DEVICE_JSON capcut_device_windows.json
  else
    set_env_value CAPCUT_DEVICE_JSON ""
  fi
  echo "CapCut provider is configured."
}

env_value() {
  local name="$1" fallback="$2"
  if [[ -f .env ]]; then
    local line
    line="$(grep -E "^[[:space:]]*${name}=" .env | tail -n 1 || true)"
    if [[ -n "$line" ]]; then echo "${line#*=}"; return; fi
  fi
  echo "$fallback"
}

run_server() {
  ensure_dirs
  copy_env_if_missing
  local py host port
  py="$(python_bin)"
  host="${HOST_VALUE:-$(env_value HOST 127.0.0.1)}"
  port="${PORT_VALUE:-$(env_value PORT 8010)}"
  export PYTHONUTF8=1
  echo "Starting server at http://${host}:${port}"
  exec "$py" -m uvicorn app:app --host "$host" --port "$port"
}

start_server() {
  ensure_dirs
  if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "Server is already running with PID $(cat "$PID_FILE")"
    exit 0
  fi
    local args=(run)
  if [[ -n "$HOST_VALUE" ]]; then args+=(--host "$HOST_VALUE"); fi
  if [[ -n "$PORT_VALUE" ]]; then args+=(--port "$PORT_VALUE"); fi
  nohup "$ROOT_DIR/vox.sh" "${args[@]}" >> "$LOG_DIR/server.out.log" 2>> "$LOG_DIR/server.err.log" &
  echo $! > "$PID_FILE"
  echo "Server started in background. PID: $(cat "$PID_FILE")"
  echo "Logs: $LOG_DIR/server.out.log, $LOG_DIR/server.err.log"
}

stop_server() {
  if [[ -f "$PID_FILE" ]]; then
    local pid
    pid="$(cat "$PID_FILE")"
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      sleep 1
      kill -9 "$pid" 2>/dev/null || true
      echo "Stopped server PID $pid"
    fi
    rm -f "$PID_FILE"
  else
    echo "No PID file."
  fi
}

status_server() {
  if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "PID file: $(cat "$PID_FILE") is running"
  else
    echo "PID file: missing or stale"
  fi
  local port
  port="${PORT_VALUE:-$(env_value PORT 8010)}"
  if command -v ss >/dev/null 2>&1; then ss -ltnp "sport = :$port" || true; else netstat -ltnp 2>/dev/null | grep ":$port" || true; fi
}

generate_key() {
  local key hash
  key="vxl_$(python3 - <<'PY'
import base64, secrets
print(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip('='))
PY
)"
  hash="$(python3 - <<PY
import hashlib
print(hashlib.sha256('$key'.encode()).hexdigest())
PY
)"
  echo "Plain key for client/extension:"
  echo "$key"
  echo
  echo "Store plain key in .env:"
  echo "LOCAL_API_KEYS=$LABEL:$key"
  echo
  echo "Recommended: store only SHA-256 hash in .env:"
  echo "LOCAL_API_KEY_HASHES=$LABEL:$hash"
}

clean_deploy() {
  local items=(.env .venv providers/capcut-tts-api audio_cache logs run __pycache__ .pytest_cache)
  if [[ "$FORCE" != "true" ]]; then echo "Dry run only. Add --force to actually delete."; fi
  for item in "${items[@]}"; do
    if [[ -e "$item" ]]; then
      if [[ "$FORCE" == "true" ]]; then rm -rf -- "$item"; echo "Removed: $item"; else echo "Would remove: $item"; fi
    fi
  done
  while IFS= read -r -d '' item; do
    if [[ "$FORCE" == "true" ]]; then rm -rf -- "$item"; echo "Removed: $item"; else echo "Would remove: $item"; fi
  done < <(find vox_local tests \( -name __pycache__ -o -name '*.pyc' -o -name '*.pyo' \) -print0 2>/dev/null)
  if [[ "$FORCE" == "true" ]]; then
    mkdir -p providers audio_cache logs run
    printf '# Provider folder\n\nRun ./vox.sh setup-capcut to clone K07VN/capcut-tts-api here.\n' > providers/README.md
    printf '# Runtime folder\n\nAudio cache is written here when the server runs.\n' > audio_cache/README.md
    printf '# Runtime logs\n\nBackground server logs are written here.\n' > logs/README.md
    printf '# Runtime PID\n\nBackground server PID files are written here.\n' > run/README.md
  fi
}

case "$COMMAND" in
  help|-h|--help) help ;;
  install) install_deps ;;
  setup) install_deps; setup_capcut; echo "Setup complete. Run ./vox.sh run" ;;
  setup-capcut) setup_capcut ;;
  run) run_server ;;
  start) start_server ;;
  stop) stop_server ;;
  status) status_server ;;
  key|generate-key) generate_key ;;
  clean|clear|clean-deploy) clean_deploy ;;
  *) help; echo "Unknown command: $COMMAND" >&2; exit 2 ;;
esac
