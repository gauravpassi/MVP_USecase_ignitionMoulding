#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo "Starting FastAPI backend..."
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
