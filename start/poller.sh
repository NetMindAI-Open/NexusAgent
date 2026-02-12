#!/bin/bash
# Start ModulePoller (detects Instance completion and triggers dependency chains)
cd "$(dirname "$0")/.."
uv run python -m xyz_agent_context.services.module_poller
