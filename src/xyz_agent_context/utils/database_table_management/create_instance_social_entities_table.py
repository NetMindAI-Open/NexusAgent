#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create instance_social_entities table

Contains SocialEntity data model and InstanceSocialEntitiesTableManager definition.

Usage:
    uv run python src/xyz_agent_context/utils/database_table_management/create_instance_social_entities_table.py
    uv run python src/xyz_agent_context/utils/database_table_management/create_instance_social_entities_table.py --force
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

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


# ===== SocialEntity Pydantic Model =====

class SocialEntity(BaseModel):
    """
    Social Entity Data Model

    Records entity (user or other Agent) information in an Instance's social network.
    Each record is associated with a ModuleInstance.
    """
    id: Optional[int] = None
    instance_id: str = Field(..., max_length=64, description="Associated ModuleInstance ID")
    entity_id: str = Field(..., max_length=64, description="Entity ID (user_id or agent_id)")
    entity_type: str = Field(..., max_length=32, description="Entity type: user | agent")
    entity_name: Optional[str] = Field(None, max_length=255, description="Entity name/nickname")
    entity_description: Optional[str] = Field(None, description="Entity brief description")
    identity_info: Dict[str, Any] = Field(default={}, description="Identity information JSON")
    contact_info: Dict[str, Any] = Field(default={}, description="Contact information JSON")
    relationship_strength: float = Field(default=0.0, description="Relationship strength 0.0-1.0")
    interaction_count: int = Field(default=0, description="Interaction count")
    last_interaction_time: Optional[datetime] = Field(None, description="Last interaction time")
    tags: List[str] = Field(default=[], description="Tag list JSON")
    expertise_domains: List[str] = Field(default=[], description="Expertise domains list JSON")
    related_job_ids: List[str] = Field(default=[], description="Related Job IDs list")
    embedding: Optional[List[float]] = Field(default=None, description="Entity semantic embedding vector")
    persona: Optional[str] = Field(default=None, description="Persona/style guide for communicating with this entity")
    extra_data: Dict[str, Any] = Field(default={}, description="Extra data JSON")
    created_at: Optional[datetime] = Field(default=None, description="Creation time")
    updated_at: Optional[datetime] = Field(default=None, description="Update time")


# ===== Instance Social Entities Table Manager =====

class InstanceSocialEntitiesTableManager(BaseTableManager):
    """instance_social_entities table manager"""
    model = SocialEntity
    table_name = "instance_social_entities"
    field_name_mapping = {}
    ignored_fields = {"created_at", "updated_at"}
    protected_columns = {"id", "created_at", "updated_at"}
    new_column_defaults = {}

    unique_id_field = None  # Composite unique key: instance_id + entity_id
    json_fields = {"identity_info", "contact_info", "tags", "expertise_domains", "related_job_ids", "extra_data", "embedding"}

    @classmethod
    def get_mysql_type(cls, field_name: str, field_type: type, field_info: Any) -> str:
        """Custom type mapping"""
        if field_name == "instance_id":
            return "VARCHAR(64) NOT NULL"
        if field_name == "entity_id":
            return "VARCHAR(64) NOT NULL"
        if field_name == "entity_type":
            return "VARCHAR(32) NOT NULL"
        if field_name == "entity_name":
            return "VARCHAR(255)"
        if field_name == "entity_description":
            return "TEXT"
        if field_name == "relationship_strength":
            return "FLOAT DEFAULT 0.0"
        if field_name == "interaction_count":
            return "INT DEFAULT 0"
        if field_name == "last_interaction_time":
            return "DATETIME(6)"
        if field_name in cls.json_fields:
            return "JSON"
        if field_name == "persona":
            return "TEXT"
        return super().get_mysql_type(field_name, field_type, field_info)


# ===== Index Definitions =====

INDEXES = [
    ("uk_instance_entity", ["instance_id", "entity_id"], True),
    ("idx_instance_id", ["instance_id"], False),
    ("idx_entity_type", ["entity_type"], False),
]


# ===== CLI =====

async def main():
    parser = argparse.ArgumentParser(description="Create instance_social_entities table")
    parser.add_argument("--force", "-f", action="store_true", help="Force drop existing table and recreate")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("instance_social_entities Table Creation Tool")
    print("=" * 60)

    if args.interactive:
        await create_table_interactive(InstanceSocialEntitiesTableManager, INDEXES)
    else:
        await create_table(InstanceSocialEntitiesTableManager, INDEXES, force=args.force)


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
