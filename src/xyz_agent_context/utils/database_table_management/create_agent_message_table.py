#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create agent_messages table

Contains AgentMessageTableManager definition. AgentMessage model is imported from schema.agent_message_schema.

Usage:
    uv run python src/xyz_agent_context/utils/database_table_management/create_agent_message_table.py
    uv run python src/xyz_agent_context/utils/database_table_management/create_agent_message_table.py --force
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any, Dict

try:
    from xyz_agent_context.schema.agent_message_schema import AgentMessage
    from xyz_agent_context.utils.database_table_management.table_manager_base import BaseTableManager
    from xyz_agent_context.utils.database_table_management.create_table_base import (
        create_table,
        create_table_interactive,
    )
except ImportError:
    project_root = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(project_root / "src"))
    from xyz_agent_context.schema.agent_message_schema import AgentMessage
    from xyz_agent_context.utils.database_table_management.table_manager_base import BaseTableManager
    from xyz_agent_context.utils.database_table_management.create_table_base import (
        create_table,
        create_table_interactive,
    )


# ===== Agent Message Table Manager =====

class AgentMessageTableManager(BaseTableManager):
    """
    Agent Messages Table Manager

    Manages the agent_messages table, used to store each Agent's message list.
    """
    model = AgentMessage
    table_name = "agent_messages"
    field_name_mapping = {"id": "id"}
    ignored_fields = set()  # Do not ignore any fields, created_at needs to be inserted
    protected_columns = {"id", "created_at"}
    new_column_defaults: Dict[str, str] = {}

    unique_id_field = "message_id"

    @classmethod
    def get_mysql_type(cls, field_name: str, field_type: type, field_info: Any) -> str:
        """Custom type mapping"""
        if field_name == "content":
            return "TEXT NOT NULL"
        return super().get_mysql_type(field_name, field_type, field_info)


# ===== Index Definitions =====

INDEXES = [
    ("idx_agent_id", ["agent_id"], False),
    ("idx_agent_source", ["agent_id", "source_type"], False),
    ("idx_created_at", ["created_at"], False),
    ("idx_if_response", ["agent_id", "if_response"], False),
]


# ===== CLI =====

async def main():
    parser = argparse.ArgumentParser(description="Create agent_messages table")
    parser.add_argument("--force", "-f", action="store_true", help="Force drop existing table and recreate")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("Agent Messages Table Creation Tool")
    print("=" * 60)

    if args.interactive:
        await create_table_interactive(AgentMessageTableManager, INDEXES)
    else:
        await create_table(AgentMessageTableManager, INDEXES, force=args.force)


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
