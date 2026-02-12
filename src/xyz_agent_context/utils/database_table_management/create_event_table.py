#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create events table

Contains EventTableManager definition. Event model is imported from narrative.models.

Usage:
    uv run python src/xyz_agent_context/utils/database_table_management/create_event_table.py
    uv run python src/xyz_agent_context/utils/database_table_management/create_event_table.py --force
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any

try:
    from xyz_agent_context.narrative.models import Event
    from xyz_agent_context.utils.database_table_management.table_manager_base import BaseTableManager
    from xyz_agent_context.utils.database_table_management.create_table_base import (
        create_table,
        create_table_interactive,
    )
except ImportError:
    project_root = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(project_root / "src"))
    from xyz_agent_context.narrative.models import Event
    from xyz_agent_context.utils.database_table_management.table_manager_base import BaseTableManager
    from xyz_agent_context.utils.database_table_management.create_table_base import (
        create_table,
        create_table_interactive,
    )


# ===== Event Table Manager =====

class EventTableManager(BaseTableManager):
    """Event table manager"""
    model = Event
    table_name = "events"
    field_name_mapping = {"id": "event_id"}
    ignored_fields = {"created_at", "updated_at"}
    protected_columns = {"id", "created_at", "updated_at"}
    new_column_defaults = {
        "event_embedding": None,
        "embedding_text": "",
    }

    unique_id_field = "event_id"
    json_fields = {
        "env_context",
        "module_instances",
        "event_log",
        "event_embedding",
    }

    # narrative_id and user_id are Optional in Event model, can be NULL at creation, backfilled later
    nullable_id_fields = {"narrative_id", "user_id"}

    @classmethod
    def get_mysql_type(cls, field_name: str, field_type: type, field_info: Any) -> str:
        """Custom type mapping (special handling for Event table)"""
        if field_name in cls.nullable_id_fields:
            return "VARCHAR(128) NULL"
        if field_name == "event_id" or field_name.endswith("_id"):
            return "VARCHAR(128) NOT NULL"
        if field_name == "final_output":
            return "TEXT NULL"
        if field_name == "event_embedding":
            return "MEDIUMTEXT"
        if field_name == "embedding_text":
            return "TEXT"
        return super().get_mysql_type(field_name, field_type, field_info)


# ===== Index Definitions =====

INDEXES = [
    ("idx_narrative_id", ["narrative_id"], False),
    ("idx_agent_id", ["agent_id"], False),
    ("idx_user_id", ["user_id"], False),
    ("idx_trigger", ["trigger"], False),
    ("idx_created_at", ["created_at"], False),
]


# ===== CLI =====

async def main():
    parser = argparse.ArgumentParser(description="Create events table")
    parser.add_argument("--force", "-f", action="store_true", help="Force drop existing table and recreate")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("Events Table Creation Tool")
    print("=" * 60)

    if args.interactive:
        await create_table_interactive(EventTableManager, INDEXES)
    else:
        await create_table(EventTableManager, INDEXES, force=args.force)


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
