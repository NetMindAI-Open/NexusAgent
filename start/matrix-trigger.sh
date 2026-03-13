#!/bin/bash
# Start MatrixTrigger — background poller for Matrix messages (NexusMatrix)
cd "$(dirname "$0")/.."
unset CLAUDECODE
uv run python -m xyz_agent_context.module.matrix_module.matrix_trigger
