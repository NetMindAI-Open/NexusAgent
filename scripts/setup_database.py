#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库初始化脚本 - 一键创建所有表

在新的 MySQL 数据库上运行此脚本，自动创建项目所需的全部数据表。

前提条件：
1. 已创建好 MySQL 数据库实例
2. 在项目根目录 .env 文件中配置好数据库连接信息

Usage:
    uv run python scripts/setup_database.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# 确保可以导入项目模块
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root / "src"))

from xyz_agent_context.utils.database import load_db_config
from xyz_agent_context.utils.db_factory import get_db_client
from xyz_agent_context.utils.database_table_management.create_table_base import (
    generate_create_table_sql,
    check_table_exists,
)
from xyz_agent_context.utils.database_table_management.create_all_tables import TABLE_CONFIGS


async def setup_database() -> None:
    """一键创建所有数据表"""

    # ===== 1. 显示配置信息 =====
    print("\n" + "=" * 60)
    print("  数据库初始化")
    print("=" * 60)

    config = load_db_config()
    print(f"\n  Host:     {config['host']}:{config.get('port', 3306)}")
    print(f"  Database: {config['database']}")
    print(f"  User:     {config['user']}")

    # ===== 2. 测试连接 =====
    print(f"\n{'─' * 60}")
    print("  测试数据库连接...")

    try:
        db = await get_db_client()
        is_connected = await db.ping()
        if not is_connected:
            print("  ✗ 数据库连接失败")
            sys.exit(1)
        print("  ✓ 数据库连接成功")
    except Exception as e:
        print(f"  ✗ 连接错误: {e}")
        sys.exit(1)

    # ===== 3. 创建所有表 =====
    print(f"\n{'─' * 60}")
    print(f"  创建 {len(TABLE_CONFIGS)} 张数据表...\n")

    results = []
    for table_name, (manager_class, indexes) in TABLE_CONFIGS.items():
        try:
            exists = await check_table_exists(table_name)
            if exists:
                results.append((table_name, "skip", "已存在"))
                print(f"  · {table_name:40} 已存在，跳过")
                continue

            create_sql = generate_create_table_sql(manager_class, indexes)
            await db.execute(create_sql, fetch=False)
            results.append((table_name, "ok", "创建成功"))
            print(f"  ✓ {table_name:40} 创建成功")

        except Exception as e:
            results.append((table_name, "fail", str(e)[:60]))
            print(f"  ✗ {table_name:40} 失败: {e}")

    # ===== 4. 汇总 =====
    created = sum(1 for _, s, _ in results if s == "ok")
    skipped = sum(1 for _, s, _ in results if s == "skip")
    failed = sum(1 for _, s, _ in results if s == "fail")

    print(f"\n{'─' * 60}")
    print(f"  完成: 新建 {created} 张, 已存在 {skipped} 张", end="")
    if failed:
        print(f", 失败 {failed} 张")
    else:
        print()
    print("=" * 60 + "\n")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(setup_database())
    except KeyboardInterrupt:
        print("\n\n操作被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n  ✗ 错误: {e}")
        sys.exit(1)
