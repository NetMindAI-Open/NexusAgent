Directory structure:

  start/
  ├── all.sh           # Start all services (tmux 5 windows)
  ├── control.sh       # Control panel (status + quit)
  ├── mcp.sh           # MCP server (7801-7805)
  ├── backend.sh       # FastAPI backend (8000)
  ├── job-trigger.sh   # Job trigger
  ├── poller.sh        # ModulePoller
  └── frontend.sh      # Frontend dev server (5173)

  Usage:

# Start all services
bash start/all.sh

# Start backend only, skip frontend
bash start/all.sh --no-fe

# Start a single service (open a separate terminal for each)
bash start/mcp.sh
bash start/backend.sh

# Enter/exit tmux
tmux attach -t xyz-dev
tmux kill-session -t xyz-dev   # Stop all

Each script auto-cd's to the project root, so they can be run from anywhere.
