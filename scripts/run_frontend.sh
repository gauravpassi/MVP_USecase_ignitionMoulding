#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo "Starting Streamlit frontend..."
python -m streamlit run frontend/app.py --server.port 8501
