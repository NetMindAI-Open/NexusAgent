#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create instance_awareness table

Contains AwarenessData data model and InstanceAwarenessTableManager definition.

Usage:
    uv run python src/xyz_agent_context/utils/database_table_management/create_instance_awareness_table.py
    uv run python src/xyz_agent_context/utils/database_table_management/create_instance_awareness_table.py --force
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

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


# ===== AwarenessData Pydantic Model =====

class AwarenessData(BaseModel):
    """
    Awareness Data Model

    Stores Agent self-awareness/cognitive information.
    Each record is associated with a ModuleInstance.
    """
    id: Optional[int] = None
    instance_id: str = Field(..., max_length=64, description="Associated ModuleInstance ID")
    awareness: str = Field(default="", description="Agent self-awareness/cognitive description (generated and updated by LLM)")
    created_at: Optional[datetime] = Field(default=None, description="Creation time")
    updated_at: Optional[datetime] = Field(default=None, description="Update time")


# ===== Instance Awareness Table Manager =====

class InstanceAwarenessTableManager(BaseTableManager):
    """instance_awareness table manager"""
    model = AwarenessData
    table_name = "instance_awareness"
    field_name_mapping = {}
    ignored_fields = {"created_at", "updated_at"}
    protected_columns = {"id", "created_at", "updated_at"}
    new_column_defaults = {}

    unique_id_field = "instance_id"

    @classmethod
    def get_mysql_type(cls, field_name: str, field_type: type, field_info: Any) -> str:
        """Custom type mapping"""
        if field_name == "instance_id":
            return "VARCHAR(64) NOT NULL"
        if field_name == "awareness":
            return "TEXT NOT NULL"
        return super().get_mysql_type(field_name, field_type, field_info)


# ===== Index Definitions =====

INDEXES = []


# ===== CLI =====

async def main():
    parser = argparse.ArgumentParser(description="Create instance_awareness table")
    parser.add_argument("--force", "-f", action="store_true", help="Force drop existing table and recreate")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("instance_awareness Table Creation Tool")
    print("=" * 60)

    if args.interactive:
        await create_table_interactive(InstanceAwarenessTableManager, INDEXES)
    else:
        await create_table(InstanceAwarenessTableManager, INDEXES, force=args.force)


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
