#!/bin/bash
# Start NexusMatrix Server (port 8953)
# NexusMatrix is a separate project under related_project/
cd "$(dirname "$0")/../related_project/NetMind-AI-RS-NexusMatrix"
unset CLAUDECODE
uv run python -m nexus_matrix.main
