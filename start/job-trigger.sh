#!/bin/bash
# Start Job trigger (polls every 60 seconds)
cd "$(dirname "$0")/.."
uv run python src/xyz_agent_context/module/job_module/job_trigger.py
