#!/bin/bash
# Start FastAPI backend (port 8000)
cd "$(dirname "$0")/.."
uv run uvicorn backend.main:app --reload --reload-dir backend --reload-dir src --port 8000
