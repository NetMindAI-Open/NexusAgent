#!/bin/bash
# Start all services (tmux multi-window)
#
# Usage:
#   bash start/all.sh          # Start all services
#   bash start/all.sh --no-fe  # Start backend only, skip frontend
#
# Management:
#   tmux attach -t xyz-dev     # Enter tmux
#   Ctrl-b + n / p             # Switch windows
#   Switch to [control] and press q  # Stop all

SESSION=xyz-dev
DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Kill existing session if present
tmux has-session -t $SESSION 2>/dev/null && tmux kill-session -t $SESSION

# Window 0: Control Panel
tmux new-session -d -s $SESSION -n control -c "$DIR"
tmux send-keys -t $SESSION:control "bash start/control.sh" C-m

# Window 1: Frontend (optionally skip)
if [ "$1" != "--no-fe" ]; then
    tmux new-window -t $SESSION -n frontend -c "$DIR"
    tmux send-keys -t $SESSION:frontend "bash start/frontend.sh" C-m
fi

# Window 2: FastAPI Backend
tmux new-window -t $SESSION -n backend -c "$DIR"
tmux send-keys -t $SESSION:backend "bash start/backend.sh" C-m

# Window 3: Job Trigger
tmux new-window -t $SESSION -n job-trigger -c "$DIR"
tmux send-keys -t $SESSION:job-trigger "bash start/job-trigger.sh" C-m

# Window 4: ModulePoller
tmux new-window -t $SESSION -n poller -c "$DIR"
tmux send-keys -t $SESSION:poller "bash start/poller.sh" C-m

# Window 5: MCP Server
tmux new-window -t $SESSION -n mcp -c "$DIR"
tmux send-keys -t $SESSION:mcp "bash start/mcp.sh" C-m

# Switch to control window and attach
tmux select-window -t $SESSION:control
tmux attach -t $SESSION
