# Database Table Management

Database table management module - used for creating and syncing database table structures.

## Directory Structure

```
database_table_management/
├── __init__.py              # Module initialization
├── README.md                # This document
├── table_manager_base.py    # Table manager base class (BaseTableManager)
├── create_table_base.py     # Base utility functions for table creation
│
├── create_all_tables.py     # Unified creation of all tables
├── sync_all_tables.py       # Unified sync of all table structures
│
├── create_agent_table.py                    # agents table
├── create_user_table.py                     # users table
├── create_event_table.py                    # events table
├── create_narrative_table.py                # narratives table
├── create_mcp_table.py                      # mcp_urls table
├── create_chat_table.py                     # inbox_table table
├── create_agent_message_table.py            # agent_messages table
├── create_module_instances_table.py         # module_instances table
├── create_instance_social_entities_table.py # instance_social_entities table
├── create_instance_jobs_table.py            # instance_jobs table
├── create_instance_rag_store_table.py       # instance_rag_store table
├── create_instance_narrative_links_table.py # instance_narrative_links table
├── create_instance_awareness_table.py       # instance_awareness table
└── create_instance_event_memory_table.py    # instance_module_report_memory / instance_json_format_memory table
```

## Quick Start

### 1. First Deployment - Create All Tables

```bash
# Create all database tables (if they don't exist)
uv run python src/xyz_agent_context/utils/database_table_management/create_all_tables.py

# Test database connection
uv run python src/xyz_agent_context/utils/database_table_management/create_all_tables.py --test-connection

# Create only specified tables
uv run python src/xyz_agent_context/utils/database_table_management/create_all_tables.py --tables agents users events
```

### 2. Table Structure Changes - Sync Table Structure

When Pydantic models change, use the sync script to sync table structures:

```bash
# View changes for all tables (dry-run mode)
uv run python src/xyz_agent_context/utils/database_table_management/sync_all_tables.py --dry-run

# Sync all table structures
uv run python src/xyz_agent_context/utils/database_table_management/sync_all_tables.py

# Interactive sync (confirm each table individually)
uv run python src/xyz_agent_context/utils/database_table_management/sync_all_tables.py --interactive

# Sync only specified tables
uv run python src/xyz_agent_context/utils/database_table_management/sync_all_tables.py --tables agents users
```

### 3. Single Table Operations

```bash
# Create a single table
uv run python src/xyz_agent_context/utils/database_table_management/create_agent_table.py

# Force recreate table (dangerous! will delete data)
uv run python src/xyz_agent_context/utils/database_table_management/create_agent_table.py --force
```

## How It Works

### create_*_table.py

Each create_*_table.py file contains:
- **Pydantic model** (defined inline or imported from schema)
- **TableManager class** (inherits BaseTableManager, defines table name, field mappings, MySQL type mappings, etc.)
- **Index definitions**
- **CLI entry point** (supports `--force` and `--interactive` flags)

Workflow:
- Check if table exists
- If table doesn't exist, generate CREATE TABLE SQL from Pydantic model and execute
- If table already exists, prompt to use sync_all_tables.py for synchronization

### sync_all_tables.py

- Compare Pydantic model with database table structure
- Generate ALTER TABLE statements to add/drop columns
- Support dry-run mode to preview changes
- Protect critical columns (id, created_at, etc.) from being dropped

## Supported Tables

| Table Name | Description |
|------|------|
| agents | Agent information table |
| users | User information table |
| events | Event records table |
| narratives | Narrative records table |
| mcp_urls | MCP service URLs table |
| inbox_table | Inbox table |
| agent_messages | Agent messages table |
| module_instances | Module instances table |
| instance_social_entities | Social network entities table |
| instance_jobs | Job scheduling table |
| instance_rag_store | RAG store table |
| instance_narrative_links | Narrative links table |
| instance_awareness | Agent self-awareness table |
| instance_module_report_memory | Module status report table |
| instance_json_format_memory | JSON format memory table |

## Notes

1. **First deployment**: Use `create_all_tables.py` to create all tables
2. **After model changes**: Use `sync_all_tables.py` to sync table structures
3. **Production environment**: Recommended to use `--dry-run` first to preview changes
4. **External code**: Should not directly reference this module; for CRUD operations use `xyz_agent_context.repository`

## Development Guide

### Adding a New Table

1. Define a Pydantic model in `xyz_agent_context/schema/` (or define inline in the create script)
2. Create `create_xxx_table.py`, defining the TableManager class and indexes
3. Register the new table in `sync_all_tables.py` and `create_all_tables.py`
4. Create the corresponding Repository class in `xyz_agent_context/repository/`

### Modifying Table Structure

1. Modify the corresponding Pydantic model
2. Run `sync_all_tables.py --tables xxx --dry-run` to preview changes
3. After confirming correctness, run `sync_all_tables.py --tables xxx` to execute changes
