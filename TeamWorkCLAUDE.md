---
name: NexusAgent Team Workflow
description: Contribution guide for AI coding assistants and community contributors.
version: 0.1.0
---

# NexusAgent Team Workflow

Guide for AI assistants and contributors. Read `CLAUDE.md` for internal conventions, `CONTRIBUTING.md` for commit/PR format.

---

## Core Concepts

```
Agent
 └── Narrative (semantic storyline — routing metadata, not content storage)
      ├── Event 1 (a complete trigger → response cycle)
      ├── Event 2 ...
      └── active_instances:
           ├── chat_xxxx   → ChatModule
           ├── social_xxxx → SocialNetworkModule
           └── job_xxxx    → JobModule
```

| Concept | What it is | Key point |
|---------|-----------|-----------|
| **Narrative** | Semantic topic thread, routed by embedding similarity | Stores only routing index (embedding, keywords, instance list) — not memory content |
| **Module** | Pluggable capability unit (Instructions + MCP Tools + Data + Hooks) | Zero coupling between modules; adding one requires no changes to others |
| **Instance** | Runtime binding of a Module within a Narrative (`{prefix}_{uuid8}`) | LLM decides which Instances to activate at Step 2 |

### AgentRuntime 7-Step Pipeline

```
Step 0    Initialize         → Load agent config, create Event, get/create Session
Step 1    Select Narrative   → Continuity check → vector search → reuse or create Narrative
Step 1.5  Load History       → Read Narrative's markdown conversation history
Step 2  ⭐ Decide Instances   → LLM decides which Module Instances are needed + execution path
Step 2.5  Sync Instances     → Persist Instance changes to DB and markdown
Step 3  ⭐ Execute            → data_gathering → context merge → LLM call (with MCP tools)
Step 4    Persist            → Save trajectory, update Event/Narrative summary
Step 5    Hooks              → Run each Module's hook_after_event_execution in parallel
Step 6    Callbacks          → Trigger downstream Instances when dependencies complete
```

### Module Integration with the Pipeline

Implement one class, register it in `MODULE_MAP`, and the pipeline handles the rest:

| Method you implement | Where the pipeline calls it |
|---------------------|---------------------------|
| `get_config()` | Step 2 — LLM reads metadata to decide whether to create an Instance |
| `hook_data_gathering(ctx_data)` | Step 3 — Your data is injected into LLM context |
| `get_instructions(ctx_data)` | Step 3 — Your prompt text is merged into system prompt |
| `get_mcp_config()` / `create_mcp_server()` | Step 3 — Your MCP tools become available to the LLM |
| `hook_after_event_execution(params)` | Step 5 — Post-event processing |

---

## Architecture

```
API Layer (FastAPI)  →  AgentRuntime (7-step)  →  Services (Narrative, Module)
                                                    ↓
                                              _*_impl/ (私有实现)
                                                    ↓
                                              Repository → AsyncDatabaseClient
```

### Key Rules

- **Module independence**: Modules never import each other; each owns its DB tables, MCP server, and hooks
- **Private packages stay private**: `_module_impl/`, `_narrative_impl/` — only used within their parent package
- **Centralized config**: `settings.py` (pydantic-settings); never use `os.getenv()` directly
- **DB access through Repository**: Table management scripts are standalone, never imported by app code
- **Generic prompts**: No hard-coded scenarios (e.g., sales); scenario logic belongs in Awareness
- **No backward compatibility**: Change things cleanly — no deprecated shims or re-exports
- **Chinese comments**, file headers follow `@file_name / @author / @date / @description` format

---

## Development

```bash
# Setup
uv sync && cp .env.example .env

# 4 backend processes + frontend
uv run python src/xyz_agent_context/module/module_runner.py mcp          # MCP servers
uv run uvicorn backend.main:app --reload --port 8000                     # API
uv run python -m xyz_agent_context.services.module_poller                # Instance poller
uv run python -m xyz_agent_context.module.job_module.job_trigger --interval 60  # Job scheduler
cd frontend && npm install && npm run dev                                # Frontend
```

### Verification

```bash
# Import check
uv run python -c "import xyz_agent_context.module; import xyz_agent_context.narrative; import xyz_agent_context.services; print('OK')"

# Schema sync (if DB schema changed)
cd src/xyz_agent_context/utils/database_table_management && uv run python sync_all_tables.py --dry-run

# Frontend build (if frontend changed)
cd frontend && npm run build
```

---

## Contributor Types

```bash
git config user.name && git config user.email  # Run first
```

| Type | Scope | Can touch |
|------|-------|-----------|
| **Core** | Full-stack | Everything (follow Key Rules above) |
| **Module** | New module | `module/<name>_module/`, `repository/`, `schema/`, table scripts, `MODULE_MAP` |
| **Frontend** | UI only | `frontend/` only |
| **Community** | Scoped to issue | Depends on issue |

---

## Adding a Module (Step-by-Step)

1. **Create** `module/<name>_module/` with `__init__.py`, `<name>_module.py`, `prompts.py`
2. **Subclass** `XYZBaseModule` — implement `get_config`, `hook_data_gathering`, `hook_after_event_execution`, `get_mcp_config`, `create_mcp_server`
3. **Register** in `module/__init__.py` → `MODULE_MAP`
4. **Table scripts**: `create_<name>_table.py` + `modify_<name>_table.py` (standalone, never imported by app code)
5. **Repository**: `repository/<name>_repository.py` extending `BaseRepository[T]` (if needed)
6. **Schema**: add Pydantic models to `schema/` (if needed)
7. **Verify**: import check + table creation + table sync dry-run

---

## Git & PR

**Branch**: `feat/<scope>/<description>` from `main`. All PRs target `main`.

**Commit**: [Conventional Commits](https://www.conventionalcommits.org/) — `feat(module): add calendar module`

**PR body**:
```
## Summary
- What and why (1-3 bullets)

## Verification
- [ ] Import check passes
- [ ] Frontend build passes (if changed)
- [ ] Table sync dry-run passes (if schema changed)
```

---

## Common Pitfalls

| Don't | Do |
|-------|-----|
| Import from `_module_impl/` outside parent package | Import from `module/` public API |
| `os.getenv()` | `from xyz_agent_context.settings import settings` |
| Import ModuleA from ModuleB | Shared logic goes in `schema/` or `utils/` |
| Hard-code scenario in prompt | Put in Awareness |
| Store memory in Narrative | Narrative is routing metadata; use Module's own DB tables |
| Add backward-compat shim | Just change it cleanly |
| `git push --force` to main | Never |
