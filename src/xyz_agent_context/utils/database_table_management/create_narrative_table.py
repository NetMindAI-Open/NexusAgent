#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create narratives table

Contains NarrativeTableManager definition. Narrative model is imported from narrative.models.

Usage:
    uv run python src/xyz_agent_context/utils/database_table_management/create_narrative_table.py
    uv run python src/xyz_agent_context/utils/database_table_management/create_narrative_table.py --force
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Any

try:
    from xyz_agent_context.narrative.models import Narrative
    from xyz_agent_context.utils.database_table_management.table_manager_base import BaseTableManager
    from xyz_agent_context.utils.database_table_management.create_table_base import (
        create_table,
        create_table_interactive,
    )
except ImportError:
    project_root = Path(__file__).resolve().parents[4]
    sys.path.insert(0, str(project_root / "src"))
    from xyz_agent_context.narrative.models import Narrative
    from xyz_agent_context.utils.database_table_management.table_manager_base import BaseTableManager
    from xyz_agent_context.utils.database_table_management.create_table_base import (
        create_table,
        create_table_interactive,
    )


# ===== Narrative Table Manager =====

class NarrativeTableManager(BaseTableManager):
    """Narrative table manager"""
    model = Narrative
    table_name = "narratives"
    field_name_mapping = {"id": "narrative_id"}
    ignored_fields = {"created_at", "updated_at"}
    protected_columns = {"id", "created_at", "updated_at"}
    new_column_defaults = {
        "topic_keywords": "[]",
        "topic_hint": "",
        "routing_embedding": None,
        "embedding_updated_at": None,
        "events_since_last_embedding_update": 0,
        "active_instances": "[]",
        "instance_history_ids": "[]",
        "is_special": "other",
    }

    unique_id_field = "narrative_id"
    json_fields = {
        "narrative_info",
        "event_ids",
        "dynamic_summary",
        "env_variables",
        "topic_keywords",
        "routing_embedding",
        "active_instances",
        "instance_history_ids",
        "related_narrative_ids",
    }

    @classmethod
    def get_mysql_type(cls, field_name: str, field_type: type, field_info: Any) -> str:
        """Custom type mapping (special handling for Narrative table)"""
        if field_name == "narrative_id":
            return "VARCHAR(128) NOT NULL"
        if field_name == "main_chat_instance_id":
            return "VARCHAR(128) NULL"
        if field_name.endswith("_id"):
            return "VARCHAR(128) NOT NULL"
        if field_name == "routing_embedding":
            return "MEDIUMTEXT"
        if field_name == "topic_hint":
            return "TEXT"
        if field_name == "is_special":
            return "VARCHAR(64) NOT NULL DEFAULT 'other'"
        return super().get_mysql_type(field_name, field_type, field_info)


# ===== Index Definitions =====

INDEXES = [
    ("idx_agent_id", ["agent_id"], False),
    ("idx_type", ["type"], False),
    ("idx_created_at", ["created_at"], False),
]


# ===== CLI =====

async def main():
    parser = argparse.ArgumentParser(description="Create narratives table")
    parser.add_argument("--force", "-f", action="store_true", help="Force drop existing table and recreate")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("Narratives Table Creation Tool")
    print("=" * 60)

    if args.interactive:
        await create_table_interactive(NarrativeTableManager, INDEXES)
    else:
        await create_table(NarrativeTableManager, INDEXES, force=args.force)


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
