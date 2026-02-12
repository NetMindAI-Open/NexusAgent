#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create instance_rag_store table

Contains RAGStoreData data model and InstanceRAGStoreTableManager definition.

Usage:
    uv run python src/xyz_agent_context/utils/database_table_management/create_instance_rag_store_table.py
    uv run python src/xyz_agent_context/utils/database_table_management/create_instance_rag_store_table.py --force
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional, Union

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


# ===== RAGStoreData Pydantic Model =====

class RAGStoreData(BaseModel):
    """
    RAG Store Data Model

    Stores metadata for Gemini File Search Store.
    Each record is associated with a ModuleInstance.
    """
    id: Optional[int] = None
    instance_id: str = Field(..., max_length=64, description="Associated ModuleInstance ID")
    display_name: str = Field(..., max_length=255, description="Store display name")
    store_name: str = Field(..., max_length=512, description="Store resource name returned by Gemini API")
    keywords: List[Union[str, dict]] = Field(default_factory=list, description="Keyword summaries of knowledge base content")
    uploaded_files: List[str] = Field(default_factory=list, description="List of uploaded file names")
    file_count: int = Field(default=0, description="Number of uploaded files")
    created_at: Optional[datetime] = Field(default=None, description="Creation time")
    updated_at: Optional[datetime] = Field(default=None, description="Update time")


# ===== Instance RAG Store Table Manager =====

class InstanceRAGStoreTableManager(BaseTableManager):
    """instance_rag_store table manager"""
    model = RAGStoreData
    table_name = "instance_rag_store"
    field_name_mapping = {}
    ignored_fields = set()
    protected_columns = {"id"}
    new_column_defaults = {}

    unique_id_field = "instance_id"
    json_fields = {"keywords", "uploaded_files"}

    @classmethod
    def get_mysql_type(cls, field_name: str, field_type: type, field_info: Any) -> str:
        """Custom type mapping"""
        if field_name == "instance_id":
            return "VARCHAR(64) NOT NULL"
        if field_name == "display_name":
            return "VARCHAR(255) NOT NULL"
        if field_name == "store_name":
            return "VARCHAR(512) NOT NULL"
        if field_name == "file_count":
            return "INT DEFAULT 0"
        if field_name in cls.json_fields:
            return "JSON"
        if field_name in ("created_at", "updated_at"):
            return "DATETIME(6)"
        return super().get_mysql_type(field_name, field_type, field_info)


# ===== Index Definitions =====

INDEXES = [
    ("uk_display_name", ["display_name"], True),
]


# ===== CLI =====

async def main():
    parser = argparse.ArgumentParser(description="Create instance_rag_store table")
    parser.add_argument("--force", "-f", action="store_true", help="Force drop existing table and recreate")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("instance_rag_store Table Creation Tool")
    print("=" * 60)

    if args.interactive:
        await create_table_interactive(InstanceRAGStoreTableManager, INDEXES)
    else:
        await create_table(InstanceRAGStoreTableManager, INDEXES, force=args.force)


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
