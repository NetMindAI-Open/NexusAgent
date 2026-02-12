#!/bin/bash
# Start MCP server (ports 7801-7805)
cd "$(dirname "$0")/.."
uv run python src/xyz_agent_context/module/module_runner.py mcp
