#!/usr/bin/env bash
#
# AegisEdge ATC — start backend + frontend
# Usage:  ./quickstart.sh
# Stop:   ./quickstart.sh --stop
#
# Options:
#   --stop           Stop any running backend/frontend processes and exit.
#   --skip-install   Skip installing backend/frontend dependencies.
#
# Backend Python dependencies are installed into a project-local virtualenv
# (.venv) rather than the global/system Python, so nothing gets installed
# system-wide.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$ROOT/.quickstart-logs"
VENV_DIR="$ROOT/.venv"
API_PORT=8000
UI_PORT=5173

STOP=0
SKIP_INSTALL=0

for arg in "$@"; do
    case "$arg" in
        --stop)
            STOP=1
            ;;
        --skip-install)
            SKIP_INSTALL=1
            ;;
        *)
            echo "Unknown option: $arg" >&2
            exit 1
            ;;
    esac
done

stop_aegisedge() {
    echo "Stopping AegisEdge processes on ports ${API_PORT} / ${UI_PORT}..."

    for port in "$API_PORT" "$UI_PORT"; do
        if command -v lsof >/dev/null 2>&1; then
            pids=$(lsof -ti tcp:"$port" 2>/dev/null || true)
            if [ -n "$pids" ]; then
                echo "$pids" | xargs kill -9 2>/dev/null || true
            fi
        fi
    done

    pkill -f "uvicorn app.main:app" 2>/dev/null || true
    pkill -f "vite --host" 2>/dev/null || true

    sleep 1
    echo "Done."
}

if [ "$STOP" -eq 1 ]; then
    stop_aegisedge
    exit 0
fi

echo "========================================"
echo "  AegisEdge ATC - Quick Start"
echo "========================================"

if ! command -v python3 >/dev/null 2>&1; then
    echo "Python not found on PATH." >&2
    exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
    echo "npm not found on PATH." >&2
    exit 1
fi

stop_aegisedge

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtualenv at $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi
PYTHON_BIN="$VENV_DIR/bin/python"
echo "Using isolated virtualenv Python: $PYTHON_BIN"

if [ "$SKIP_INSTALL" -eq 0 ]; then
    echo "[1/3] Backend dependencies..."
    "$PYTHON_BIN" -m pip install -r "$ROOT/backend/requirements.txt" -q

    echo "[2/3] Frontend dependencies..."
    pushd "$ROOT/frontend" >/dev/null
    if [ ! -d "node_modules" ]; then
        npm install
    fi
    popd >/dev/null
else
    echo "[1-2/3] Skipping installs (--skip-install)"
fi

echo "[3/3] Starting API + UI..."
echo "  API  http://127.0.0.1:${API_PORT}"
echo "  UI   http://127.0.0.1:${UI_PORT}"
echo "  Docs http://127.0.0.1:${API_PORT}/docs"
echo "  Stop with: ./quickstart.sh --stop"
echo ""

mkdir -p "$LOG_DIR"

(
    cd "$ROOT/backend"
    "$PYTHON_BIN" -m uvicorn app.main:app --reload --host 127.0.0.1 --port "$API_PORT"
) >"$LOG_DIR/api.log" 2>&1 &
API_PID=$!

sleep 2

(
    cd "$ROOT/frontend"
    npx vite --host 127.0.0.1 --port "$UI_PORT"
) >"$LOG_DIR/ui.log" 2>&1 &
UI_PID=$!

echo "Spawned API (pid $API_PID, log: $LOG_DIR/api.log) and UI (pid $UI_PID, log: $LOG_DIR/ui.log)."
echo "Tail logs with: tail -f $LOG_DIR/api.log $LOG_DIR/ui.log"
