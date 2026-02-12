#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create users table

Contains User data model and UserTableManager definition.

Usage:
    uv run python src/xyz_agent_context/utils/database_table_management/create_user_table.py
    uv run python src/xyz_agent_context/utils/database_table_management/create_user_table.py --force
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

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


# ===== User Status Enum =====

class UserStatus(str, Enum):
    """User status enumeration"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    BLOCKED = "blocked"
    DELETED = "deleted"


# ===== User Pydantic Model =====

class User(BaseModel):
    """User data model"""
    id: Optional[int] = None
    user_id: str = Field(..., max_length=64, description="User unique identifier")
    user_type: str = Field(..., max_length=32, description="User type")
    display_name: Optional[str] = Field(None, max_length=255, description="Display name")
    email: Optional[str] = Field(None, max_length=255, description="Email")
    phone_number: Optional[str] = Field(None, max_length=32, description="Phone number")
    nickname: Optional[str] = Field(None, max_length=50, description="Nickname")
    timezone: str = Field(default="UTC", max_length=64, description="User timezone (IANA format, e.g., Asia/Shanghai)")
    status: UserStatus = Field(default=UserStatus.ACTIVE, description="User status")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")
    last_login_time: Optional[datetime] = Field(default=None, description="Last login time")
    create_time: Optional[datetime] = Field(default=None, description="Creation time")
    update_time: Optional[datetime] = Field(default=None, description="Update time")


# ===== User Table Manager =====

class UserTableManager(BaseTableManager):
    """User table manager"""
    model = User
    table_name = "users"
    field_name_mapping = {"id": "id"}
    ignored_fields = {"create_time", "update_time"}
    protected_columns = {"id", "create_time", "update_time"}
    new_column_defaults: Dict[str, str] = {
        "timezone": "'UTC'"
    }

    unique_id_field = "user_id"
    json_fields = {"metadata"}


# ===== Index Definitions =====

INDEXES = [
    ("idx_user_type", ["user_type"], False),
    ("idx_status", ["status"], False),
]


# ===== CLI =====

async def main():
    parser = argparse.ArgumentParser(description="Create users table")
    parser.add_argument("--force", "-f", action="store_true", help="Force drop existing table and recreate")
    parser.add_argument("--interactive", "-i", action="store_true", help="Interactive mode")

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("Users Table Creation Tool")
    print("=" * 60)

    if args.interactive:
        await create_table_interactive(UserTableManager, INDEXES)
    else:
        await create_table(UserTableManager, INDEXES, force=args.force)


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
