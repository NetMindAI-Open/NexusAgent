#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create mcp_urls table

Contains MCPUrl data model and MCPTableManager definition.

Usage:
    uv run python src/xyz_agent_context/utils/database_table_management/create_mcp_table.py
    uv run python src/xyz_agent_context/utils/database_table_management/create_mcp_table.py --force
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


# ===== MCP Pydantic Model =====

class MCPUrl(BaseModel):
    """
    MCP URL Data Model

    Corresponds to the structure of the mcp_urls database table, isolated by agent_id + user_id
    """
    id: Optional[int] = None
    mcp_id: str = Field(..., max_length=64, description="MCP unique identifier")
    agent_id: str = Field(..., max_length=64, description="Agent unique identifier")
    user_id: str = Field(..., max_length=64, description="User unique identifier")
    name: str = Field(..., max_length=255, description="MCP name")
    url: str = Field(..., max_length=1024, description="MCP SSE URL")
    description: Optional[str] = Field(None, max_length=512, description="MCP description")
    is_enabled: bool = Field(default=True, description="Whether enabled")
    connection_status: Optional[str] = Field(None, max_length=32, description="Connection status")
    last_check_time: Optional[datetime] = Field(default=None, description="Last check time")
    last_error: Optional[str] = Field(None, max_length=1024, description="Last error message")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    created_at: Optional[datetime] = Field(default=None, description="Creation time")
    updated_at: Optional[datetime] = Field(default=None, description="Update time")


# ===== MCP Table Manager =====

class MCPTableManager(BaseTableManager):
    """MCP URLs table manager"""
    model = MCPUrl
    table_name = "mcp_urls"
    field_name_mapping = {"id": "id"}
    ignored_fields = {"created_at", "updated_at"}
    protected_columns = {"id", "created_at", "updated_at"}
    new_column_defaults: Dict[str, str] = {}

    unique_id_field = "mcp_id"
    json_fields = {"metadata"}


# ===== Index Definitions =====

INDEXES = [
    ("idx_agent_user", ["agent_id", "user_id"], False),
    ("idx_is_enabled", ["is_enabled"], False),
]


# ===== CLI =====

async def main():
    parser = argparse.ArgumentParser(description="Create mcp_urls table")
    parser.add_argument("--force", "-f", action="store_true", help="Force drop existing table and recreate")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("MCP URLs Table Creation Tool")
    print("=" * 60)

    if args.interactive:
        await create_table_interactive(MCPTableManager, INDEXES)
    else:
        await create_table(MCPTableManager, INDEXES, force=args.force)


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
