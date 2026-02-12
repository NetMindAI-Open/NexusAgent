#!/usr/bin/env python3
"""
删除 Narrative 及其关联数据的脚本

用法:
    uv run python scripts/delete_narrative.py <narrative_id>
    uv run python scripts/delete_narrative.py <narrative_id> --dry-run  # 预览模式，不实际删除
    uv run python scripts/delete_narrative.py <narrative_id> --force    # 强制删除，不需要确认

示例:
    uv run python scripts/delete_narrative.py nar_e1eecbe9f8b14873
    uv run python scripts/delete_narrative.py nar_e1eecbe9f8b14873 --dry-run

删除的数据包括:
1. Narrative 本身
2. Instance-Narrative 关联 (instance_narrative_links)
3. 关联的 Module Instances (module_instances)
4. 关联的 Jobs (instance_jobs)
5. Instance 的 Memory 数据 (instance_json_format_memory_*)
6. Narrative 的 Memory 数据 (json_format_event_memory_*)
7. 关联的 Events (events)
"""

import asyncio
import argparse
import sys
from typing import List, Dict, Any, Set
from dotenv import load_dotenv

load_dotenv()

from loguru import logger


async def get_narrative_info(db, narrative_id: str) -> Dict[str, Any]:
    """获取 Narrative 基本信息"""
    query = """
        SELECT narrative_id, agent_id, type, is_special, topic_hint, created_at
        FROM narratives
        WHERE narrative_id = %s
    """
    rows = await db.execute(query, (narrative_id,), fetch=True)
    if rows:
        return dict(rows[0])
    return {}


async def get_linked_instances(db, narrative_id: str) -> List[str]:
    """获取关联的 Instance IDs"""
    query = """
        SELECT instance_id FROM instance_narrative_links
        WHERE narrative_id = %s
    """
    rows = await db.execute(query, (narrative_id,), fetch=True)
    return [row['instance_id'] for row in rows] if rows else []


async def get_instance_details(db, instance_ids: List[str]) -> List[Dict[str, Any]]:
    """获取 Instance 详细信息"""
    if not instance_ids:
        return []

    placeholders = ', '.join(['%s'] * len(instance_ids))
    query = f"""
        SELECT instance_id, module_class, user_id, status, description
        FROM module_instances
        WHERE instance_id IN ({placeholders})
    """
    rows = await db.execute(query, tuple(instance_ids), fetch=True)
    return [dict(row) for row in rows] if rows else []


async def get_jobs_for_narrative(db, narrative_id: str) -> List[Dict[str, Any]]:
    """获取 Narrative 关联的 Jobs"""
    query = """
        SELECT job_id, instance_id, title, status
        FROM instance_jobs
        WHERE narrative_id = %s
    """
    rows = await db.execute(query, (narrative_id,), fetch=True)
    return [dict(row) for row in rows] if rows else []


async def get_events_for_narrative(db, narrative_id: str) -> List[str]:
    """获取 Narrative 关联的 Event IDs（从 narratives.event_ids JSON 字段）"""
    query = """
        SELECT event_ids FROM narratives WHERE narrative_id = %s
    """
    rows = await db.execute(query, (narrative_id,), fetch=True)
    if rows and rows[0].get('event_ids'):
        import json
        event_ids = rows[0]['event_ids']
        if isinstance(event_ids, str):
            event_ids = json.loads(event_ids)
        return event_ids if event_ids else []
    return []


async def get_memory_tables(db) -> List[str]:
    """获取所有 Memory 相关的表"""
    # 使用 %% 转义 LIKE 语句中的 %
    query = """
        SELECT TABLE_NAME as tbl FROM information_schema.tables
        WHERE table_schema = DATABASE()
        AND (TABLE_NAME LIKE 'json_format_event_memory_%%'
             OR TABLE_NAME LIKE 'instance_json_format_memory_%%')
    """
    rows = await db.execute(query, params=(), fetch=True)
    return [row['tbl'] for row in rows] if rows else []


async def delete_narrative_data(
    db,
    narrative_id: str,
    dry_run: bool = False
) -> Dict[str, int]:
    """
    删除 Narrative 及其所有关联数据

    Returns:
        删除统计 {table_name: deleted_count}
    """
    stats = {}

    # 1. 获取关联的 Instance IDs
    instance_ids = await get_linked_instances(db, narrative_id)
    logger.info(f"找到 {len(instance_ids)} 个关联的 Instances")

    # 2. 获取关联的 Event IDs
    event_ids = await get_events_for_narrative(db, narrative_id)
    logger.info(f"找到 {len(event_ids)} 个关联的 Events")

    # 3. 获取所有 Memory 表
    memory_tables = await get_memory_tables(db)
    logger.info(f"找到 {len(memory_tables)} 个 Memory 表")

    if dry_run:
        logger.info("=== DRY RUN 模式，不实际删除 ===")

    # ========== 开始删除 ==========

    # 4. 删除 Instance 的 Memory (instance_json_format_memory_*)
    for table in memory_tables:
        if table.startswith('instance_json_format_memory_') and instance_ids:
            placeholders = ', '.join(['%s'] * len(instance_ids))
            if dry_run:
                count_query = f"SELECT COUNT(*) as cnt FROM `{table}` WHERE instance_id IN ({placeholders})"
                result = await db.execute(count_query, tuple(instance_ids), fetch=True)
                count = result[0]['cnt'] if result else 0
            else:
                delete_query = f"DELETE FROM `{table}` WHERE instance_id IN ({placeholders})"
                result = await db.execute(delete_query, tuple(instance_ids), fetch=False)
                count = result if isinstance(result, int) else 0

            if count > 0:
                stats[table] = count
                logger.info(f"  {'将删除' if dry_run else '已删除'} {table}: {count} 条")

    # 5. 删除 Narrative 的 Memory (json_format_event_memory_*)
    for table in memory_tables:
        if table.startswith('json_format_event_memory_'):
            if dry_run:
                count_query = f"SELECT COUNT(*) as cnt FROM `{table}` WHERE narrative_id = %s"
                result = await db.execute(count_query, (narrative_id,), fetch=True)
                count = result[0]['cnt'] if result else 0
            else:
                delete_query = f"DELETE FROM `{table}` WHERE narrative_id = %s"
                result = await db.execute(delete_query, (narrative_id,), fetch=False)
                count = result if isinstance(result, int) else 0

            if count > 0:
                stats[table] = count
                logger.info(f"  {'将删除' if dry_run else '已删除'} {table}: {count} 条")

    # 6. 删除 Jobs (instance_jobs)
    if dry_run:
        count_query = "SELECT COUNT(*) as cnt FROM instance_jobs WHERE narrative_id = %s"
        result = await db.execute(count_query, (narrative_id,), fetch=True)
        count = result[0]['cnt'] if result else 0
    else:
        delete_query = "DELETE FROM instance_jobs WHERE narrative_id = %s"
        result = await db.execute(delete_query, (narrative_id,), fetch=False)
        count = result if isinstance(result, int) else 0

    if count > 0:
        stats['instance_jobs'] = count
        logger.info(f"  {'将删除' if dry_run else '已删除'} instance_jobs: {count} 条")

    # 7. 删除 Instance-Narrative Links
    if dry_run:
        count_query = "SELECT COUNT(*) as cnt FROM instance_narrative_links WHERE narrative_id = %s"
        result = await db.execute(count_query, (narrative_id,), fetch=True)
        count = result[0]['cnt'] if result else 0
    else:
        delete_query = "DELETE FROM instance_narrative_links WHERE narrative_id = %s"
        result = await db.execute(delete_query, (narrative_id,), fetch=False)
        count = result if isinstance(result, int) else 0

    if count > 0:
        stats['instance_narrative_links'] = count
        logger.info(f"  {'将删除' if dry_run else '已删除'} instance_narrative_links: {count} 条")

    # 8. 删除 Module Instances（只删除非公共的、且只关联到这个 Narrative 的）
    if instance_ids:
        # 找出只关联到这个 Narrative 的 Instances
        for inst_id in instance_ids:
            # 检查这个 Instance 是否还关联到其他 Narrative
            check_query = """
                SELECT COUNT(*) as cnt FROM instance_narrative_links
                WHERE instance_id = %s AND narrative_id != %s
            """
            result = await db.execute(check_query, (inst_id, narrative_id), fetch=True)
            other_links = result[0]['cnt'] if result else 0

            if other_links == 0:
                # 这个 Instance 只关联到当前 Narrative，可以删除
                # 但要检查是否是公共 Instance
                is_public_query = "SELECT is_public FROM module_instances WHERE instance_id = %s"
                pub_result = await db.execute(is_public_query, (inst_id,), fetch=True)
                is_public = pub_result[0]['is_public'] if pub_result else False

                if not is_public:
                    if not dry_run:
                        delete_query = "DELETE FROM module_instances WHERE instance_id = %s"
                        await db.execute(delete_query, (inst_id,), fetch=False)

                    stats['module_instances'] = stats.get('module_instances', 0) + 1
                    logger.info(f"  {'将删除' if dry_run else '已删除'} module_instance: {inst_id}")

    # 9. 删除 Events
    if event_ids:
        placeholders = ', '.join(['%s'] * len(event_ids))
        if dry_run:
            count_query = f"SELECT COUNT(*) as cnt FROM events WHERE event_id IN ({placeholders})"
            result = await db.execute(count_query, tuple(event_ids), fetch=True)
            count = result[0]['cnt'] if result else 0
        else:
            delete_query = f"DELETE FROM events WHERE event_id IN ({placeholders})"
            result = await db.execute(delete_query, tuple(event_ids), fetch=False)
            count = result if isinstance(result, int) else 0

        if count > 0:
            stats['events'] = count
            logger.info(f"  {'将删除' if dry_run else '已删除'} events: {count} 条")

    # 10. 删除 Narrative 本身
    if dry_run:
        count_query = "SELECT COUNT(*) as cnt FROM narratives WHERE narrative_id = %s"
        result = await db.execute(count_query, (narrative_id,), fetch=True)
        count = result[0]['cnt'] if result else 0
    else:
        delete_query = "DELETE FROM narratives WHERE narrative_id = %s"
        result = await db.execute(delete_query, (narrative_id,), fetch=False)
        count = result if isinstance(result, int) else 0

    if count > 0:
        stats['narratives'] = count
        logger.info(f"  {'将删除' if dry_run else '已删除'} narratives: {count} 条")

    return stats


async def main():
    parser = argparse.ArgumentParser(
        description="删除 Narrative 及其关联数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  uv run python scripts/delete_narrative.py nar_e1eecbe9f8b14873
  uv run python scripts/delete_narrative.py nar_e1eecbe9f8b14873 --dry-run
  uv run python scripts/delete_narrative.py nar_e1eecbe9f8b14873 --force
"""
    )

    parser.add_argument(
        "narrative_id",
        help="要删除的 Narrative ID"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式，只显示将要删除的内容，不实际删除"
    )

    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="强制删除，不需要确认"
    )

    args = parser.parse_args()

    # 初始化数据库连接
    from xyz_agent_context.utils import get_db_client
    db = await get_db_client()

    narrative_id = args.narrative_id

    print("=" * 70)
    print(f"删除 Narrative: {narrative_id}")
    print("=" * 70)

    # 1. 获取 Narrative 信息
    narrative_info = await get_narrative_info(db, narrative_id)
    if not narrative_info:
        print(f"\n❌ 错误: Narrative '{narrative_id}' 不存在")
        sys.exit(1)

    print(f"\n📖 Narrative 信息:")
    print(f"   ID: {narrative_info.get('narrative_id')}")
    print(f"   Agent: {narrative_info.get('agent_id')}")
    print(f"   Type: {narrative_info.get('type')}")
    print(f"   Special: {narrative_info.get('is_special')}")
    print(f"   Created: {narrative_info.get('created_at')}")
    topic = narrative_info.get('topic_hint', '')
    if topic:
        print(f"   Topic: {topic[:80]}...")

    # 2. 获取关联数据
    instance_ids = await get_linked_instances(db, narrative_id)
    instance_details = await get_instance_details(db, instance_ids)
    jobs = await get_jobs_for_narrative(db, narrative_id)
    event_ids = await get_events_for_narrative(db, narrative_id)

    print(f"\n📊 关联数据:")
    print(f"   Instances: {len(instance_ids)}")
    for inst in instance_details:
        print(f"      - {inst['instance_id']} ({inst['module_class']}) user={inst['user_id']}")

    print(f"   Jobs: {len(jobs)}")
    for job in jobs:
        print(f"      - {job['job_id']}: {job['title'][:40]} [{job['status']}]")

    print(f"   Events: {len(event_ids)}")

    # 3. 确认删除
    if args.dry_run:
        print(f"\n🔍 DRY RUN 模式 - 预览将要删除的数据:")
    elif not args.force:
        print(f"\n⚠️  警告: 此操作将永久删除上述所有数据!")
        confirm = input("确认删除? (输入 'yes' 继续): ")
        if confirm.lower() != 'yes':
            print("已取消")
            sys.exit(0)

    # 4. 执行删除
    print(f"\n{'🔍 预览' if args.dry_run else '🗑️  删除'}中...")
    stats = await delete_narrative_data(db, narrative_id, dry_run=args.dry_run)

    # 5. 显示结果
    print(f"\n{'📋 预览' if args.dry_run else '✅ 删除'}结果:")
    total = 0
    for table, count in stats.items():
        print(f"   {table}: {count} 条")
        total += count
    print(f"   ─────────────────")
    print(f"   总计: {total} 条")

    if args.dry_run:
        print(f"\n💡 这是预览模式。要实际删除，请去掉 --dry-run 参数。")


if __name__ == "__main__":
    asyncio.run(main())
