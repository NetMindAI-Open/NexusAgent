#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create module_instances table

Contains ModuleInstancesTableManager definition. ModuleInstanceRecord model is imported from schema.instance_schema.

Usage:
    uv run python src/xyz_agent_context/utils/database_table_management/create_module_instances_table.py
    uv run python src/xyz_agent_context/utils/database_table_management/create_module_instances_table.py --force
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any

try:
    from xyz_agent_context.schema.instance_schema import ModuleInstanceRecord
    from xyz_agent_context.utils.database_table_management.table_manager_base import BaseTableManager
    from xyz_agent_context.utils.database_table_management.create_table_base import (
        create_table,
        create_table_interactive,
    )
except ImportError:
    project_root = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(project_root / "src"))
    from xyz_agent_context.schema.instance_schema import ModuleInstanceRecord
    from xyz_agent_context.utils.database_table_management.table_manager_base import BaseTableManager
    from xyz_agent_context.utils.database_table_management.create_table_base import (
        create_table,
        create_table_interactive,
    )


# ===== Module Instances Table Manager =====

class ModuleInstancesTableManager(BaseTableManager):
    """module_instances table manager"""
    model = ModuleInstanceRecord
    table_name = "module_instances"
    field_name_mapping = {}
    ignored_fields = {"created_at", "updated_at"}
    protected_columns = {"id", "created_at", "updated_at"}
    new_column_defaults = {
        "dependencies": "[]",
        "config": "{}",
        "keywords": "[]",
        "callback_processed": "0",
    }

    unique_id_field = "instance_id"
    json_fields = {
        "dependencies",
        "config",
        "state",
        "routing_embedding",
        "keywords",
    }

    @classmethod
    def get_mysql_type(cls, field_name: str, field_type: type, field_info: Any) -> str:
        """Custom type mapping (special handling for module_instances table)"""
        if field_name == "instance_id":
            return "VARCHAR(64) NOT NULL"
        if field_name in ("agent_id", "user_id"):
            if field_name == "user_id":
                return "VARCHAR(128) NULL"
            return "VARCHAR(128) NOT NULL"
        if field_name == "module_class":
            return "VARCHAR(64) NOT NULL"
        if field_name == "is_public":
            return "TINYINT(1) NOT NULL DEFAULT 0"
        if field_name == "status":
            return "ENUM('active', 'in_progress', 'blocked', 'completed', 'failed', 'archived') NOT NULL DEFAULT 'active'"
        if field_name in ("description", "topic_hint"):
            return "TEXT NULL"
        if field_name == "routing_embedding":
            return "MEDIUMTEXT NULL"
        if field_name in ("last_used_at", "completed_at", "archived_at"):
            return "DATETIME(6) NULL"
        if field_name == "last_polled_status":
            return "VARCHAR(32) NULL"
        if field_name == "callback_processed":
            return "TINYINT(1) NOT NULL DEFAULT 0"
        return super().get_mysql_type(field_name, field_type, field_info)


# ===== Index Definitions =====

INDEXES = [
    ("idx_agent_id", ["agent_id"], False),
    ("idx_agent_user", ["agent_id", "user_id"], False),
    ("idx_module_class", ["module_class"], False),
    ("idx_status", ["status"], False),
    ("idx_is_public", ["agent_id", "is_public"], False),
]


# ===== CLI =====

async def main():
    parser = argparse.ArgumentParser(description="Create module_instances table")
    parser.add_argument("--force", "-f", action="store_true", help="Force drop existing table and recreate")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("module_instances Table Creation Tool")
    print("=" * 60)

    if args.interactive:
        await create_table_interactive(ModuleInstancesTableManager, INDEXES)
    else:
        await create_table(ModuleInstancesTableManager, INDEXES, force=args.force)


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
