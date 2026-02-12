#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create inbox_table table

Contains InboxTableManager definition. InboxMessage model is imported from schema.inbox_schema.

Usage:
    uv run python src/xyz_agent_context/utils/database_table_management/create_chat_table.py
    uv run python src/xyz_agent_context/utils/database_table_management/create_chat_table.py --force
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Dict

try:
    from xyz_agent_context.schema.inbox_schema import InboxMessage
    from xyz_agent_context.utils.database_table_management.table_manager_base import BaseTableManager
    from xyz_agent_context.utils.database_table_management.create_table_base import (
        create_table,
        create_table_interactive,
    )
except ImportError:
    project_root = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(project_root / "src"))
    from xyz_agent_context.schema.inbox_schema import InboxMessage
    from xyz_agent_context.utils.database_table_management.table_manager_base import BaseTableManager
    from xyz_agent_context.utils.database_table_management.create_table_base import (
        create_table,
        create_table_interactive,
    )


# ===== Inbox Table Manager =====

class InboxTableManager(BaseTableManager):
    """
    Inbox Table Manager

    Manages the inbox_table table, Inbox is the data store for ChatModule's messaging capability.
    """
    model = InboxMessage
    table_name = "inbox_table"
    field_name_mapping = {"id": "id"}
    ignored_fields = set()  # Do not ignore any fields, created_at needs to be inserted
    protected_columns = {"id", "created_at"}
    new_column_defaults: Dict[str, str] = {}

    unique_id_field = "message_id"
    json_fields = {"source"}


# ===== Index Definitions =====

INDEXES = [
    ("idx_user_id", ["user_id"], False),
    ("idx_is_read", ["is_read"], False),
]


# ===== CLI =====

async def main():
    parser = argparse.ArgumentParser(description="Create inbox_table table")
    parser.add_argument("--force", "-f", action="store_true", help="Force drop existing table and recreate")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("Inbox Table Creation Tool")
    print("=" * 60)

    if args.interactive:
        await create_table_interactive(InboxTableManager, INDEXES)
    else:
        await create_table(InboxTableManager, INDEXES, force=args.force)


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
