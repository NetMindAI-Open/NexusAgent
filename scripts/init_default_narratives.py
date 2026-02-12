#!/usr/bin/env python3
"""
测试和初始化默认 Narratives 的脚本

用途：
1. 为指定的 agent 初始化 8 个默认 Narrative
2. 验证默认 Narratives 是否正确创建
3. 查询和显示默认 Narratives

Usage:
    # 为 agent 初始化默认 Narratives
    uv run python scripts/init_default_narratives.py --agent-id agent_001
    
    # 为 agent 和 user 初始化
    uv run python scripts/init_default_narratives.py --agent-id agent_001 --user-id user_001
    
    # 只查看配置，不创建
    uv run python scripts/init_default_narratives.py --show-config
    
    # 验证已存在的默认 Narratives
    uv run python scripts/init_default_narratives.py --agent-id agent_001 --verify-only
"""

from __future__ import annotations

import asyncio
import argparse
import sys
from pathlib import Path
from typing import Optional

# 添加项目根目录到 Python 路径
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root / "src"))

from xyz_agent_context.narrative import (
    NarrativeService,
    DEFAULT_NARRATIVES_CONFIG,
    ensure_default_narratives,
    get_all_default_narrative_names,
    get_all_default_narrative_codes,
)


def show_config():
    """显示默认 Narratives 的配置"""
    print("=" * 80)
    print("8 个默认 Narrative 的配置")
    print("=" * 80)
    print()
    
    for i, config in enumerate(DEFAULT_NARRATIVES_CONFIG, 1):
        print(f"{i}. {config['code']} - {config['name']}")
        print(f"   描述: {config['description']}")
        print(f"   示例: {', '.join(config['examples'][:3])}")
        if len(config['examples']) > 3:
            print(f"        ... 等 {len(config['examples'])} 个示例")
        print()
    
    print("=" * 80)


async def verify_narratives(agent_id: str):
    """验证 agent 的默认 Narratives"""
    print("=" * 80)
    print(f"验证 Agent {agent_id} 的默认 Narratives")
    print("=" * 80)
    print()
    
    service = NarrativeService(agent_id=agent_id)
    
    found_count = 0
    missing_count = 0
    
    for config in DEFAULT_NARRATIVES_CONFIG:
        narrative_code = config["code"]
        narrative_name = config["name"]
        narrative_id = f"{agent_id}_default_{narrative_code}"
        
        try:
            narrative = await service.load_narrative_from_db(narrative_id)
            
            if narrative:
                print(f"✅ {narrative_code} ({narrative_name})")
                print(f"   ID: {narrative.id}")
                print(f"   is_special: {narrative.is_special}")
                print(f"   Events: {len(narrative.event_ids)}")
                found_count += 1
            else:
                print(f"❌ {narrative_code} ({narrative_name}) - 不存在")
                missing_count += 1
                
        except Exception as e:
            print(f"❌ {narrative_code} ({narrative_name}) - 查询失败: {e}")
            missing_count += 1
        
        print()
    
    print("=" * 80)
    print(f"验证结果: 找到 {found_count} 个, 缺失 {missing_count} 个")
    print("=" * 80)
    
    return found_count, missing_count


async def init_narratives(agent_id: str, user_id: Optional[str] = None):
    """为 agent 初始化默认 Narratives"""
    print("=" * 80)
    print(f"初始化 Agent {agent_id} 的默认 Narratives")
    if user_id:
        print(f"User ID: {user_id}")
    print("=" * 80)
    print()
    
    service = NarrativeService(agent_id=agent_id)
    
    # 确保默认 Narratives 存在
    try:
        narratives = await ensure_default_narratives(
            agent_id=agent_id,
            user_id=user_id,
            narrative_service=service
        )
        
        print()
        print("=" * 80)
        print("初始化完成！")
        print("=" * 80)
        print()
        print(f"成功初始化了 {len(narratives)} 个默认 Narrative:")
        print()
        
        for name, narrative in narratives.items():
            print(f"  • {name}")
            print(f"    ID: {narrative.id}")
            print(f"    类型: {narrative.type.value}")
            print(f"    is_special: {narrative.is_special}")
            print()
        
        return narratives
        
    except Exception as e:
        print(f"[ERROR] 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main() -> int:
    """主函数"""
    parser = argparse.ArgumentParser(
        description="初始化和验证默认 Narratives"
    )
    parser.add_argument(
        "--agent-id",
        type=str,
        help="Agent ID"
    )
    parser.add_argument(
        "--user-id",
        type=str,
        help="User ID（可选）"
    )
    parser.add_argument(
        "--show-config",
        action="store_true",
        help="只显示配置，不进行任何操作"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="只验证，不创建"
    )
    
    args = parser.parse_args()
    
    # 显示配置
    if args.show_config:
        show_config()
        return 0
    
    # 检查必需的参数
    if not args.agent_id:
        parser.print_help()
        print()
        print("[ERROR] 必须提供 --agent-id 参数")
        return 1
    
    try:
        if args.verify_only:
            # 只验证
            found, missing = await verify_narratives(args.agent_id)
            return 0 if missing == 0 else 1
        else:
            # 初始化
            narratives = await init_narratives(args.agent_id, args.user_id)
            
            if narratives:
                print()
                print("✅ 所有默认 Narratives 已就绪！")
                print()
                print("可以使用以下命令验证:")
                print(f"  uv run python scripts/init_default_narratives.py --agent-id {args.agent_id} --verify-only")
                return 0
            else:
                return 1
        
    except Exception as e:
        print(f"\n[ERROR] 发生错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    raise SystemExit(exit_code)

