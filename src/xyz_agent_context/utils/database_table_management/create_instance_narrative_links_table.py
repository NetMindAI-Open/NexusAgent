#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create instance_narrative_links table

Contains InstanceNarrativeLinksTableManager definition.
InstanceNarrativeLink model is imported from schema.instance_schema.

Usage:
    uv run python src/xyz_agent_context/utils/database_table_management/create_instance_narrative_links_table.py
    uv run python src/xyz_agent_context/utils/database_table_management/create_instance_narrative_links_table.py --force
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any

try:
    from xyz_agent_context.schema.instance_schema import InstanceNarrativeLink
    from xyz_agent_context.utils.database_table_management.table_manager_base import BaseTableManager
    from xyz_agent_context.utils.database_table_management.create_table_base import (
        create_table,
        create_table_interactive,
    )
except ImportError:
    project_root = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(project_root / "src"))
    from xyz_agent_context.schema.instance_schema import InstanceNarrativeLink
    from xyz_agent_context.utils.database_table_management.table_manager_base import BaseTableManager
    from xyz_agent_context.utils.database_table_management.create_table_base import (
        create_table,
        create_table_interactive,
    )


# ===== Instance Narrative Links Table Manager =====

class InstanceNarrativeLinksTableManager(BaseTableManager):
    """instance_narrative_links table manager"""
    model = InstanceNarrativeLink
    table_name = "instance_narrative_links"
    field_name_mapping = {}
    ignored_fields = {"created_at", "updated_at"}
    protected_columns = {"id", "created_at", "updated_at"}
    new_column_defaults = {}

    unique_id_field = None  # Composite unique key

    @classmethod
    def get_mysql_type(cls, field_name: str, field_type: type, field_info: Any) -> str:
        """Custom type mapping"""
        if field_name in ("instance_id", "narrative_id"):
            return "VARCHAR(128) NOT NULL"
        if field_name == "link_type":
            return "ENUM('active', 'history', 'shared') NOT NULL DEFAULT 'active'"
        if field_name == "local_status":
            return "ENUM('active', 'in_progress', 'blocked', 'completed', 'failed') NOT NULL DEFAULT 'active'"
        if field_name in ("linked_at", "unlinked_at"):
            return "DATETIME(6) NULL"
        return super().get_mysql_type(field_name, field_type, field_info)


# ===== Index Definitions =====

INDEXES = [
    ("uk_instance_narrative", ["instance_id", "narrative_id"], True),
    ("idx_narrative_id", ["narrative_id"], False),
    ("idx_instance_id", ["instance_id"], False),
    ("idx_link_type", ["link_type"], False),
]


# ===== CLI =====

async def main():
    parser = argparse.ArgumentParser(description="Create instance_narrative_links table")
    parser.add_argument("--force", "-f", action="store_true", help="Force drop existing table and recreate")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("instance_narrative_links Table Creation Tool")
    print("=" * 60)

    if args.interactive:
        await create_table_interactive(InstanceNarrativeLinksTableManager, INDEXES)
    else:
        await create_table(InstanceNarrativeLinksTableManager, INDEXES, force=args.force)


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
