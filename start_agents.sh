#!/usr/bin/env bash
set -euo pipefail

python -m pip install -r requirements.txt >/dev/null 2>&1 || true

(uvicorn apps.writer.main:app --host 0.0.0.0 --port 8001) &
WRITER_PID=$!
(uvicorn apps.researcher.main:app --host 0.0.0.0 --port 8002) &
RESEARCHER_PID=$!
(streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 8501) &
STREAMLIT_PID=$!

cleanup() {
  kill "$WRITER_PID" "$RESEARCHER_PID" "$STREAMLIT_PID" 2>/dev/null || true
}
trap cleanup EXIT

wait "$WRITER_PID" "$RESEARCHER_PID" "$STREAMLIT_PID"
