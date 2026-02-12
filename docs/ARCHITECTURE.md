# Architecture

## Overview

```
                       +---------------------------+
                       |    Frontend (React 19)    |
                       |    WebSocket + REST API   |
                       +------------+--------------+
                                    |
                       +------------v--------------+
                       |    API Layer (FastAPI)     |
                       +------------+--------------+
                                    |
                       +------------v--------------+
                       |       AgentRuntime        |
                       |    (7-step orchestrator)   |
                       +--+-------+-------+--------+
                          |       |       |
              +-----------+  +----+----+  +-----------+
              |              |         |              |
     +--------v---+   +-----v----+ +--v----------+ +-v-----------+
     | Narrative   |   | Module   | | Context     | | Agent       |
     | Service     |   | Service  | | Runtime     | | Framework   |
     | (memory)    |   | (ability)| | (prompts)   | | (LLM SDKs) |
     +--------+----+   +-----+----+ +-------------+ +-------------+
              |              |
     +--------v--------------v--------+
     |       Repository Layer          |
     |    (async MySQL via aiomysql)   |
     +---------------------------------+
```

Each layer depends only on the layers below it. Modules participate in AgentRuntime's 7-step execution flow via the Hook mechanism.

## Service Architecture

`bash run.sh run` starts all the following services:

| Service | Port | Description |
|---------|------|-------------|
| Frontend | 5173 | React dev server |
| FastAPI Backend | 8000 | REST API + WebSocket |
| MCP Servers | 7801-7805 | Module Tool Servers |
| Job Trigger | - | Background scheduled task executor |
| Module Poller | - | Instance status polling & dependency chain trigger |
| MySQL | 3306 | Primary database |
| EverMemOS Web | 1995 | Memory system API |
| MongoDB | 27017 | EverMemOS document storage |
| Elasticsearch | 19200 | EverMemOS full-text search |
| Milvus | 19530 | Vector database |
| Redis | 6379 | Cache |

## Modules

All feature modules inherit from `XYZBaseModule` and participate in the Agent execution flow via the Hook mechanism. Each module is self-contained and does not reference other modules:

| Module | Instance Prefix | MCP Port | Description |
|--------|----------------|----------|-------------|
| **Memory** | -- | -- | Infrastructure: EverMemOS semantic memory (highest priority, runs first) |
| **Awareness** | `aware_` | 7801 | Agent self-awareness: personality, goals, behavioral guidelines |
| **BasicInfo** | `basic_` | -- | Static agent information + creator identification (no MCP) |
| **Chat** | `chat_` | 7804 | Multi-user chat history, inbox system, dual-track memory |
| **SocialNetwork** | `social_` | 7802 | Entity graph: track people, relationships, interaction history |
| **Job** | `job_` | 7803 | Task scheduling & dependency chains (one-shot / cron / periodic / continuous) |
| **GeminiRAG** | `rag_` | 7805 | RAG based on Google Gemini File Search API |
| **Skill** | -- | -- | Three-tier skill management (system / agent / user), filesystem-based |
| **EventMemory** | -- | -- | Infrastructure: per-narrative event storage for other modules |

Each module is self-contained under `src/xyz_agent_context/module/<name>_module/`.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Runtime | Python 3.13, asyncio |
| API | FastAPI, uvicorn, SSE, WebSocket |
| Database | MySQL 8 via aiomysql (async) |
| Memory | EverMemOS (MongoDB + Elasticsearch + Milvus + Redis) |
| LLM | Claude Agent SDK, OpenAI Agents SDK, Google Gemini API |
| Tool Protocol | MCP (Model Context Protocol) via fastmcp |
| Data Validation | Pydantic v2, pydantic-settings |
| Frontend | React 19, TypeScript, Vite, Zustand, Tailwind CSS |
| Package Managers | uv (Python), npm (frontend) |
| Deploy | Docker, systemd, nginx, tmux |

## Project Structure

```
backend/                    # FastAPI app (standalone package)
  main.py                   #   Entry point, lifecycle, CORS
  routes/                   #   REST + WebSocket endpoints

frontend/                   # React 19 + TypeScript + Vite + Zustand

start/                      # Startup scripts (tmux-based)
  all.sh                    #   One-click start all (5 services)
  control.sh                #   Status dashboard + one-key stop
  mcp.sh / backend.sh / ... #   Individual service launchers

src/xyz_agent_context/      # Core library
  agent_runtime/            #   7-step orchestrator + step implementations
  agent_framework/          #   LLM SDK adapters (Claude, OpenAI, Gemini)
  context_runtime/          #   Dynamic system prompt builder
  narrative/                #   Long-term memory: narratives, events, sessions
  module/                   #   Module system: base class, loader, service, hook manager
    memory_module/          #     EverMemOS semantic memory (infrastructure)
    awareness_module/
    basic_info_module/
    chat_module/
    social_network_module/
    job_module/
    gemini_rag_module/
    skill_module/
    event_memory_module/
  schema/                   #   Pydantic data models (centralized)
  repository/               #   Data access layer (BaseRepository pattern)
  services/                 #   Background services (ModulePoller, InstanceSync)
  utils/                    #   Database client, embedding, evermemos client, table mgmt
    evermemos/              #     EverMemOS HTTP API client

run.sh                      # Unified entry (install / run / status / stop)
docker-compose.yaml         # MySQL Docker configuration
deploy/                     # Production deploy (systemd + nginx)
```
