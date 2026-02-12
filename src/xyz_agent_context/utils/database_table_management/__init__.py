#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Database Table Management Module

This module contains all database table management scripts:
1. table_manager_base.py - Table manager base class (BaseTableManager)
2. create_*_table.py - TableManager definitions and creation scripts for each table
3. create_all_tables.py - Batch creation of all tables
4. sync_all_tables.py - Unified table structure sync tool

Usage:
- create_*_table.py: Define TableManager and Pydantic models, supports table creation
- sync_all_tables.py: For syncing table structure (adding/removing columns)
- create_all_tables.py: For batch creation of all tables

Notes:
- This module is a standalone collection of table management scripts
- External code should not directly reference the contents of this module
- CRUD operations should use repository classes in xyz_agent_context.repository
"""

# Do not export anything; this module is a standalone script collection
__all__ = []
