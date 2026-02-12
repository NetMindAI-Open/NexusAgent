#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create instance_event_memory related tables

Contains the following models and TableManagers:
1. InstanceModuleReportMemory + InstanceModuleReportMemoryTableManager
2. InstanceJsonFormatMemory + InstanceJsonFormatMemoryTableManager

Usage:
    uv run python src/xyz_agent_context/utils/database_table_management/create_instance_event_memory_table.py
    uv run python src/xyz_agent_context/utils/database_table_management/create_instance_event_memory_table.py --force
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


# ===== Report Memory Model =====

class InstanceModuleReportMemory(BaseModel):
    """
    Module Status Report Model

    Used for Module to report its status to Narrative.
    Each record is associated with a ModuleInstance.
    """
    id: Optional[int] = None
    instance_id: str = Field(..., max_length=64, description="Associated ModuleInstance ID")
    report_memory: Optional[str] = Field(default=None, description="Status report content (natural language description)")
    created_at: Optional[datetime] = Field(default=None, description="Creation time")
    updated_at: Optional[datetime] = Field(default=None, description="Update time")


class InstanceModuleReportMemoryTableManager(BaseTableManager):
    """instance_module_report_memory table manager"""
    model = InstanceModuleReportMemory
    table_name = "instance_module_report_memory"
    field_name_mapping = {}
    ignored_fields = {"created_at", "updated_at"}
    protected_columns = {"id", "created_at", "updated_at"}
    new_column_defaults = {}

    unique_id_field = "instance_id"

    @classmethod
    def get_mysql_type(cls, field_name: str, field_type: type, field_info: Any) -> str:
        if field_name == "instance_id":
            return "VARCHAR(64) NOT NULL"
        if field_name == "report_memory":
            return "TEXT"
        return super().get_mysql_type(field_name, field_type, field_info)


# ===== JSON Format Memory Model =====

class InstanceJsonFormatMemory(BaseModel):
    """
    JSON Format Memory Model

    Stores structured data of a Module (e.g., ChatModule's conversation history).
    Each record is associated with a ModuleInstance.
    """
    id: Optional[int] = None
    instance_id: str = Field(..., max_length=64, description="Associated ModuleInstance ID")
    memory: Optional[str] = Field(default=None, description="JSON format memory data")
    created_at: Optional[datetime] = Field(default=None, description="Creation time")
    updated_at: Optional[datetime] = Field(default=None, description="Update time")


class InstanceJsonFormatMemoryTableManager(BaseTableManager):
    """instance_json_format_memory table manager"""
    model = InstanceJsonFormatMemory
    table_name = "instance_json_format_memory"
    field_name_mapping = {}
    ignored_fields = {"created_at", "updated_at"}
    protected_columns = {"id", "created_at", "updated_at"}
    new_column_defaults = {}

    unique_id_field = "instance_id"

    @classmethod
    def get_mysql_type(cls, field_name: str, field_type: type, field_info: Any) -> str:
        if field_name == "instance_id":
            return "VARCHAR(64) NOT NULL"
        if field_name == "memory":
            return "MEDIUMTEXT"
        return super().get_mysql_type(field_name, field_type, field_info)


# ===== Index Definitions =====

REPORT_MEMORY_INDEXES = []

JSON_FORMAT_MEMORY_INDEXES = []


# ===== CLI =====

async def main():
    parser = argparse.ArgumentParser(description="Create instance_event_memory related tables")
    parser.add_argument("--force", "-f", action="store_true", help="Force drop existing tables and recreate")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("instance_event_memory Table Creation Tool")
    print("=" * 60)

    # Create instance_module_report_memory table
    print("\n[1/2] Creating instance_module_report_memory table")
    print("-" * 60)
    if args.interactive:
        await create_table_interactive(InstanceModuleReportMemoryTableManager, REPORT_MEMORY_INDEXES)
    else:
        await create_table(InstanceModuleReportMemoryTableManager, REPORT_MEMORY_INDEXES, force=args.force)

    # Create instance_json_format_memory table
    print("\n[2/2] Creating instance_json_format_memory table")
    print("-" * 60)
    if args.interactive:
        await create_table_interactive(InstanceJsonFormatMemoryTableManager, JSON_FORMAT_MEMORY_INDEXES)
    else:
        await create_table(InstanceJsonFormatMemoryTableManager, JSON_FORMAT_MEMORY_INDEXES, force=args.force)

    print("\n" + "=" * 60)
    print("All tables created")
    print("=" * 60)


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
