# Development Guide

## Manual Setup

If you prefer setting up each component manually instead of using `bash run.sh`.

### 1. Database

```bash
docker run -d --name nexus-mysql \
  -e MYSQL_ROOT_PASSWORD=dev -e MYSQL_DATABASE=xyz_agent \
  -p 3306:3306 mysql:8
```

### 2. Install Dependencies

```bash
uv sync
cd frontend && npm install && cd ..
```

### 3. Configure

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Required -- Claude Code must be installed and authenticated separately
# (npm install -g @anthropic-ai/claude-code)

# Required -- used for embeddings and as alternative LLM
OPENAI_API_KEY="sk-..."

# Optional -- enables RAG Knowledge Base (Gemini File Search)
GOOGLE_API_KEY="..."

# Database
DB_HOST="localhost"
DB_PORT=3306
DB_NAME="xyz_agent"
DB_USER="root"
DB_PASSWORD="dev"

# Auth
ADMIN_SECRET_KEY="your-secret-key"
```

### 4. Initialize Tables

```bash
uv run python src/xyz_agent_context/utils/database_table_management/create_all_tables.py
```

### 5. Start

One command to start all services (5 processes in tmux):

```bash
bash start/all.sh
```

Or start backend only:

```bash
bash start/all.sh --no-fe
```

Or start each service individually:

```bash
# Terminal 1 -- MCP servers (ports 7801-7805)
uv run python src/xyz_agent_context/module/module_runner.py mcp

# Terminal 2 -- FastAPI (port 8000)
uv run uvicorn backend.main:app --reload --port 8000

# Terminal 3 -- ModulePoller
uv run python -m xyz_agent_context.services.module_poller

# Terminal 4 -- JobTrigger
uv run python -m xyz_agent_context.module.job_module.job_trigger --interval 60

# Terminal 5 -- Frontend (port 5173)
cd frontend && npm run dev
```

The app is available at `http://localhost:5173`, API at `http://localhost:8000`.

---

## Configuration

All configuration is managed via environment variables (loaded by `pydantic-settings` from `.env`).

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | **Yes** | OpenAI API key (embeddings + alternative LLM) |
| `GOOGLE_API_KEY` | Optional | Google Gemini API key (enables RAG Knowledge Base) |
| `DB_HOST` | Yes | MySQL host (default: `localhost`) |
| `DB_PORT` | Yes | MySQL port (default: `3306`) |
| `DB_NAME` | Yes | Database name |
| `DB_USER` | Yes | Database user |
| `DB_PASSWORD` | Yes | Database password |
| `DATABASE_URL` | No | Full MySQL connection string, overrides individual `DB_*` vars |
| `ADMIN_SECRET_KEY` | Yes | Admin auth key |
| `BASE_WORKING_PATH` | No | Agent workspace file directory (default: `./agent_workspace`) |

---

## Table Management

Database schema is managed by scripts in `src/xyz_agent_context/utils/database_table_management/`.

```bash
# Preview changes (dry run)
uv run python sync_all_tables.py --dry-run

# Apply changes
uv run python sync_all_tables.py

# Create all tables from scratch
uv run python create_all_tables.py
```

Each module has its own `create_*_table.py` and `modify_*_table.py` scripts. These scripts are standalone -- they are not imported by application code.

---

## tmux Session Management

All services run in the `xyz-dev` tmux session:

```bash
tmux attach -t xyz-dev   # Attach to session
```

| Shortcut | Action |
|----------|--------|
| `Ctrl-b` + `n` | Next window |
| `Ctrl-b` + `p` | Previous window |
| `Ctrl-b` + `number` | Jump to window |

| Window | Name | Service |
|--------|------|---------|
| 0 | control | Status panel (press `q` to stop all) |
| 1 | frontend | React frontend (5173) |
| 2 | backend | FastAPI backend (8000) |
| 3 | job-trigger | Scheduled task executor |
| 4 | poller | Module status polling |
| 5 | mcp | MCP tool servers (7801-7805) |

---

## Adding a New Module

1. Create `src/xyz_agent_context/module/<name>_module/<name>_module.py`
2. Inherit `XYZBaseModule` and implement:
   - `get_config()` -- return a `ModuleConfig` with name, prefix, description, version
   - `hook_data_gathering()` -- collect data into `ContextData`
   - `hook_after_event_execution()` -- post-execution logic
   - `get_mcp_config()` -- return MCP server config (or `None`)
3. Register in `MODULE_MAP` in `module/__init__.py`
4. Create table scripts in `utils/database_table_management/`
5. If the module needs persistence, create a Repository class in `repository/`

---

## Production Deployment

The `deploy/` directory contains a complete systemd + nginx deployment solution:

```bash
sudo bash deploy/deploy.sh     # One-click deploy (install systemd services + nginx config)
sudo bash deploy/restart.sh    # Restart all services
sudo bash deploy/update.sh     # Pull latest code and restart
```
