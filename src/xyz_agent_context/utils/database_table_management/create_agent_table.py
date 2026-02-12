#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create agents table

Contains Agent data model and AgentTableManager definition.

Usage:
    uv run python src/xyz_agent_context/utils/database_table_management/create_agent_table.py
    uv run python src/xyz_agent_context/utils/database_table_management/create_agent_table.py --force
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

try:
    from xyz_agent_context.utils.database_table_management.table_manager_base import BaseTableManager
    from xyz_agent_context.utils.database_table_management.create_table_base import (
        create_table,
        create_table_interactive,
    )
except ImportError:
    project_root = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(project_root / "src"))
    from xyz_agent_context.utils.database_table_management.table_manager_base import BaseTableManager
    from xyz_agent_context.utils.database_table_management.create_table_base import (
        create_table,
        create_table_interactive,
    )


# ===== Agent Pydantic Model =====

class Agent(BaseModel):
    """
    Agent Data Model

    Corresponds to the structure of the agents database table
    """
    # Database auto-increment ID (only used when reading from database)
    id: Optional[int] = None

    # Required fields
    agent_id: str = Field(..., max_length=64, description="Agent unique identifier")
    agent_name: str = Field(..., max_length=255, description="Agent name")
    created_by: str = Field(..., max_length=64, description="Creator")

    # Optional fields
    agent_description: Optional[str] = Field(None, max_length=255, description="Agent description")
    agent_type: Optional[str] = Field(None, max_length=32, description="Agent type")
    is_public: bool = Field(default=False, description="Whether publicly visible (visible to all users)")
    agent_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")

    # Timestamps (auto-managed by database)
    agent_create_time: Optional[datetime] = Field(default=None, description="Creation time")
    agent_update_time: Optional[datetime] = Field(default=None, description="Update time")


# ===== Agent Table Manager =====

class AgentTableManager(BaseTableManager):
    """
    Agent Table Manager

    Inherits from BaseTableManager, only needs to configure table-specific attributes
    All common CRUD and table sync logic is provided by the base class
    """
    model = Agent
    table_name = "agents"
    field_name_mapping = {"id": "id"}
    ignored_fields = {"agent_create_time", "agent_update_time"}
    protected_columns = {"id", "agent_create_time", "agent_update_time"}
    new_column_defaults: Dict[str, str] = {"is_public": "0"}

    unique_id_field = "agent_id"
    json_fields = {"agent_metadata"}


# ===== Index Definitions =====

INDEXES = [
    ("idx_created_by", ["created_by"], False),
    ("idx_agent_type", ["agent_type"], False),
    ("idx_create_time", ["agent_create_time"], False),
]


# ===== CLI =====

async def main():
    parser = argparse.ArgumentParser(description="Create agents table")
    parser.add_argument("--force", "-f", action="store_true", help="Force drop existing table and recreate")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("Agents Table Creation Tool")
    print("=" * 60)

    if args.interactive:
        await create_table_interactive(AgentTableManager, INDEXES)
    else:
        await create_table(AgentTableManager, INDEXES, force=args.force)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nOperation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
