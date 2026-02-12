#!/usr/bin/env python3
"""
@file_name: test_entity_semantic_search.py
@author: NetMind.AI
@date: 2026-01-16
@description: Entity 语义搜索功能测试脚本 (Feature 2.3)

测试目标：
1. 测试 embedding 生成和存储
2. 测试 semantic_search 方法
3. 测试 search_social_network MCP 工具的 semantic 模式

使用方式：
    cd /path/to/project
    uv run python scripts/test_entity_semantic_search.py

    # 清理测试数据
    uv run python scripts/test_entity_semantic_search.py --cleanup
"""

import asyncio
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from loguru import logger

# 配置日志
logger.remove()
logger.add(sys.stderr, level="DEBUG", format="<green>{time:HH:mm:ss}</green> | <level>{level:8}</level> | <cyan>{message}</cyan>")


# =============================================================================
# 测试常量
# =============================================================================

TEST_AGENT_ID = "test_agent_semantic_search"
TEST_INSTANCE_ID = f"social_{TEST_AGENT_ID}"

# 测试用户数据（模拟不同类型的客户）
TEST_ENTITIES = [
    {
        "entity_id": "user_alice_interested",
        "entity_name": "Alice",
        "entity_description": "Asked about GPU pricing and requested a demo. Showed strong interest in the product and asked about next steps.",
        "tags": ["potential_customer", "gpu"],
    },
    {
        "entity_id": "user_bob_hesitating",
        "entity_name": "Bob",
        "entity_description": "Inquired about features but said they need to discuss with their manager before deciding. Seems concerned about budget.",
        "tags": ["potential_customer", "enterprise"],
    },
    {
        "entity_id": "user_charlie_technical",
        "entity_name": "Charlie",
        "entity_description": "A machine learning expert who discussed technical requirements for model training. Very knowledgeable about CUDA and deep learning frameworks.",
        "tags": ["expert:ML", "technical"],
    },
    {
        "entity_id": "user_diana_frustrated",
        "entity_name": "Diana",
        "entity_description": "Expressed frustration about slow response time and requested a refund. Previous customer with support issues.",
        "tags": ["existing_customer", "support"],
    },
    {
        "entity_id": "user_eve_price_sensitive",
        "entity_name": "Eve",
        "entity_description": "Asked about discounts and compared pricing with competitors. Looking for the best deal, very price-sensitive.",
        "tags": ["potential_customer", "price_sensitive"],
    },
]


# =============================================================================
# 数据库操作
# =============================================================================

async def get_db():
    """获取数据库客户端"""
    from xyz_agent_context.utils.db_factory import get_db_client
    return await get_db_client()


# =============================================================================
# 测试数据准备
# =============================================================================

async def setup_test_data():
    """设置测试数据"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("Setting up test data for semantic search...")
    logger.info("=" * 60)

    db = await get_db()

    # 1. 确保 Agent 存在
    agent = await db.get_one("agents", {"agent_id": TEST_AGENT_ID})
    if not agent:
        await db.insert("agents", {
            "agent_id": TEST_AGENT_ID,
            "agent_name": "Semantic Search Test Agent",
            "agent_description": "Agent for testing Entity semantic search",
            "agent_type": "chat",
            "created_by": "test_user",
            "agent_create_time": datetime.now(),
        })
        logger.success(f"Created Agent: {TEST_AGENT_ID}")
    else:
        logger.info(f"Agent already exists: {TEST_AGENT_ID}")

    # 2. 创建 SocialNetworkModule Instance
    instance = await db.get_one("module_instances", {"instance_id": TEST_INSTANCE_ID})
    if not instance:
        await db.insert("module_instances", {
            "instance_id": TEST_INSTANCE_ID,
            "agent_id": TEST_AGENT_ID,
            "module_class": "SocialNetworkModule",
            "is_public": True,
            "status": "active",
            "description": "Test SocialNetworkModule Instance",
            "dependencies": json.dumps([]),
            "config": json.dumps({}),
            "keywords": json.dumps([]),
            "topic_hint": "",
            "created_at": datetime.now(),
        })
        logger.success(f"Created Instance: {TEST_INSTANCE_ID}")
    else:
        logger.info(f"Instance already exists: {TEST_INSTANCE_ID}")

    # 3. 创建测试 Entities（不带 embedding，后面测试生成）
    from xyz_agent_context.repository import SocialNetworkRepository

    repo = SocialNetworkRepository(db)

    for entity_data in TEST_ENTITIES:
        existing = await repo.get_entity(
            entity_id=entity_data["entity_id"],
            instance_id=TEST_INSTANCE_ID
        )
        if not existing:
            await repo.add_entity(
                entity_id=entity_data["entity_id"],
                entity_type="user",
                instance_id=TEST_INSTANCE_ID,
                entity_name=entity_data["entity_name"],
                entity_description=entity_data["entity_description"],
                tags=entity_data["tags"],
            )
            logger.success(f"Created Entity: {entity_data['entity_name']}")
        else:
            # 更新 description 以确保测试数据一致
            await repo.update_entity_info(
                entity_id=entity_data["entity_id"],
                instance_id=TEST_INSTANCE_ID,
                updates={
                    "entity_description": entity_data["entity_description"],
                    "tags": json.dumps(entity_data["tags"]),
                }
            )
            logger.info(f"Entity already exists, updated: {entity_data['entity_name']}")

    logger.success("Test data setup complete!")
    return {
        "agent_id": TEST_AGENT_ID,
        "instance_id": TEST_INSTANCE_ID,
    }


# =============================================================================
# 测试 1: Embedding 生成
# =============================================================================

async def test_embedding_generation(test_data: Dict[str, str]):
    """测试 embedding 生成"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("Test 1: Embedding Generation")
    logger.info("=" * 60)

    from xyz_agent_context.module.social_network_module import SocialNetworkModule
    from xyz_agent_context.repository import SocialNetworkRepository

    db = await get_db()
    repo = SocialNetworkRepository(db)

    # 创建 SocialNetworkModule 实例
    module = SocialNetworkModule(
        agent_id=test_data["agent_id"],
        user_id="test_user",
        instance_id=test_data["instance_id"],
        database_client=db
    )

    success_count = 0
    for entity_data in TEST_ENTITIES:
        entity_id = entity_data["entity_id"]

        # 调用 _update_entity_embedding 方法
        await module._update_entity_embedding(entity_id, test_data["instance_id"])

        # 验证 embedding 是否已生成
        entity = await repo.get_entity(entity_id, test_data["instance_id"])

        if entity and entity.embedding:
            logger.success(f"  ✓ {entity.entity_name}: embedding generated (dim={len(entity.embedding)})")
            success_count += 1
        else:
            logger.error(f"  ✗ {entity_data['entity_name']}: embedding NOT generated")

    logger.info(f"\nEmbedding generation: {success_count}/{len(TEST_ENTITIES)} succeeded")
    return success_count == len(TEST_ENTITIES)


# =============================================================================
# 测试 2: Repository semantic_search 方法
# =============================================================================

async def test_semantic_search_repository(test_data: Dict[str, str]):
    """测试 Repository 层的 semantic_search 方法"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("Test 2: Repository semantic_search")
    logger.info("=" * 60)

    from xyz_agent_context.repository import SocialNetworkRepository
    from xyz_agent_context.utils.embedding_utils import get_embedding

    db = await get_db()
    repo = SocialNetworkRepository(db)

    # 定义测试查询
    test_queries = [
        {
            "query": "Who showed purchase interest?",
            "expected_top": "Alice",  # Alice showed strong interest
        },
        {
            "query": "Who is hesitating or needs approval?",
            "expected_top": "Bob",  # Bob needs to discuss with manager
        },
        {
            "query": "Who is a technical expert in machine learning?",
            "expected_top": "Charlie",  # Charlie is ML expert
        },
        {
            "query": "Who is frustrated or has support issues?",
            "expected_top": "Diana",  # Diana is frustrated
        },
        {
            "query": "Who is price-sensitive or looking for discounts?",
            "expected_top": "Eve",  # Eve is price-sensitive
        },
    ]

    success_count = 0
    for test in test_queries:
        query = test["query"]
        expected_top = test["expected_top"]

        logger.info(f"\n  Query: \"{query}\"")

        # 生成查询的 embedding
        query_embedding = await get_embedding(query)

        # 执行语义搜索
        results = await repo.semantic_search(
            instance_id=test_data["instance_id"],
            query_embedding=query_embedding,
            limit=5,
            min_similarity=0.2
        )

        if results:
            # 显示搜索结果
            logger.info(f"  Results ({len(results)} found):")
            for i, (entity, score) in enumerate(results[:3]):
                marker = "→" if entity.entity_name == expected_top else " "
                logger.info(f"    {marker} {i+1}. {entity.entity_name}: {score:.3f}")

            # 检查期望的结果是否在前 3 名
            top_names = [entity.entity_name for entity, _ in results[:3]]
            if expected_top in top_names:
                logger.success(f"  ✓ Expected '{expected_top}' found in top 3")
                success_count += 1
            else:
                logger.warning(f"  ✗ Expected '{expected_top}' NOT in top 3")
        else:
            logger.error(f"  ✗ No results found")

    logger.info(f"\nSemantic search: {success_count}/{len(test_queries)} queries matched expected results")
    return success_count >= len(test_queries) * 0.6  # 至少 60% 成功


# =============================================================================
# 测试 3: search_social_network MCP 工具
# =============================================================================

async def test_search_social_network_tool(test_data: Dict[str, str]):
    """测试 search_social_network MCP 工具的 semantic 模式"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("Test 3: search_social_network MCP Tool (semantic mode)")
    logger.info("=" * 60)

    from xyz_agent_context.module.social_network_module import SocialNetworkModule

    db = await get_db()

    # 创建 SocialNetworkModule 实例
    module = SocialNetworkModule(
        agent_id=test_data["agent_id"],
        user_id="test_user",
        instance_id=test_data["instance_id"],
        database_client=db
    )

    # 测试用例
    test_cases = [
        {
            "query": "谁最近表现出购买意向？",
            "expected_contains": "Alice",
        },
        {
            "query": "哪些客户对价格比较敏感？",
            "expected_contains": "Eve",
        },
        {
            "query": "who needs technical support?",
            "expected_contains": "Diana",
        },
    ]

    success_count = 0
    for test in test_cases:
        query = test["query"]
        expected = test["expected_contains"]

        logger.info(f"\n  Query: \"{query}\"")

        # 调用 search_network 方法（模拟 MCP 工具调用）
        result = await module.search_network(
            search_keyword=query,
            instance_id=test_data["instance_id"],
            search_type="semantic",
            top_k=3
        )

        if result["success"]:
            logger.info(f"  Results ({result['count']} found):")
            for i, entity in enumerate(result["results"][:3]):
                name = entity.get("entity_name", "Unknown")
                score = entity.get("similarity_score", 0)
                marker = "→" if name == expected else " "
                logger.info(f"    {marker} {i+1}. {name}: {score:.3f}")

            # 检查期望的结果是否存在
            result_names = [e.get("entity_name") for e in result["results"]]
            if expected in result_names:
                logger.success(f"  ✓ Expected '{expected}' found in results")
                success_count += 1
            else:
                logger.warning(f"  ✗ Expected '{expected}' NOT in results")
        else:
            logger.error(f"  ✗ Search failed: {result.get('message', 'Unknown error')}")

    logger.info(f"\nMCP tool test: {success_count}/{len(test_cases)} queries matched expected results")
    return success_count >= len(test_cases) * 0.6


# =============================================================================
# 测试 4: _summarize_new_entity_info 方法
# =============================================================================

async def test_summarize_entity_info(test_data: Dict[str, str]):
    """测试 _summarize_new_entity_info 生成的摘要质量"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("Test 4: _summarize_new_entity_info")
    logger.info("=" * 60)

    from xyz_agent_context.module.social_network_module import SocialNetworkModule

    db = await get_db()

    module = SocialNetworkModule(
        agent_id=test_data["agent_id"],
        user_id="test_user",
        instance_id=test_data["instance_id"],
        database_client=db
    )

    # 模拟对话场景
    test_conversations = [
        {
            "input": "Hi, I'm interested in your GPU products. What's the pricing?",
            "output": "Hello! Our GPU products range from $500 to $5000 depending on the model. Would you like me to send you a detailed pricing sheet?",
            "expected_keywords": ["GPU", "pricing", "interested"],
        },
        {
            "input": "I need to discuss this with my manager before we can proceed.",
            "output": "Of course, I understand. Take your time to discuss with your team. Feel free to reach out when you're ready.",
            "expected_keywords": ["manager", "discuss"],
        },
        {
            "input": "I'm a data scientist working on large language models. I need high-memory GPUs for training.",
            "output": "For LLM training, I'd recommend our A100 80GB or H100 GPUs. They're optimized for large model training.",
            "expected_keywords": ["data scientist", "LLM", "training", "GPU"],
        },
    ]

    success_count = 0
    for test in test_conversations:
        logger.info(f"\n  User: \"{test['input'][:50]}...\"")
        logger.info(f"  Agent: \"{test['output'][:50]}...\"")

        # 调用摘要方法
        summary = await module._summarize_new_entity_info(
            input_content=test["input"],
            final_output=test["output"]
        )

        logger.info(f"  Summary: \"{summary}\"")

        # 检查摘要是否包含期望的关键词
        summary_lower = summary.lower()
        matched_keywords = [kw for kw in test["expected_keywords"] if kw.lower() in summary_lower]

        if len(matched_keywords) >= 1:
            logger.success(f"  ✓ Summary contains expected keywords: {matched_keywords}")
            success_count += 1
        else:
            logger.warning(f"  ✗ Summary missing expected keywords. Expected: {test['expected_keywords']}")

    logger.info(f"\nSummary generation: {success_count}/{len(test_conversations)} produced good summaries")
    return success_count >= len(test_conversations) * 0.5


# =============================================================================
# 清理测试数据
# =============================================================================

async def cleanup_test_data():
    """清理测试数据"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("Cleaning up test data...")
    logger.info("=" * 60)

    db = await get_db()

    # 删除测试数据
    cleanup_queries = [
        (f"DELETE FROM instance_social_entities WHERE instance_id = %s", (TEST_INSTANCE_ID,)),
        (f"DELETE FROM module_instances WHERE instance_id = %s", (TEST_INSTANCE_ID,)),
        (f"DELETE FROM agents WHERE agent_id = %s", (TEST_AGENT_ID,)),
    ]

    for query, params in cleanup_queries:
        try:
            await db.execute(query, params=params, fetch=False)
            table_name = query.split("FROM")[1].split("WHERE")[0].strip()
            logger.info(f"Cleaned {table_name}")
        except Exception as e:
            logger.warning(f"Could not execute cleanup: {e}")

    logger.success("Cleanup complete!")


# =============================================================================
# 主函数
# =============================================================================

async def main():
    parser = argparse.ArgumentParser(description="Entity Semantic Search Test")
    parser.add_argument("--cleanup", action="store_true", help="Clean up test data only")
    parser.add_argument("--skip-setup", action="store_true", help="Skip test data setup")
    args = parser.parse_args()

    if args.cleanup:
        await cleanup_test_data()
        return

    logger.info("")
    logger.info("=" * 60)
    logger.info("Feature 2.3: Entity Semantic Search Test")
    logger.info("=" * 60)

    # 设置测试数据
    if not args.skip_setup:
        test_data = await setup_test_data()
    else:
        test_data = {
            "agent_id": TEST_AGENT_ID,
            "instance_id": TEST_INSTANCE_ID,
        }

    # 运行测试
    results = {}

    try:
        # 测试 1: Embedding 生成
        results["embedding_generation"] = await test_embedding_generation(test_data)

        # 测试 2: Repository semantic_search
        results["semantic_search_repo"] = await test_semantic_search_repository(test_data)

        # 测试 3: MCP 工具 semantic 模式
        results["search_tool_semantic"] = await test_search_social_network_tool(test_data)

        # 测试 4: 摘要生成质量
        results["summarize_entity_info"] = await test_summarize_entity_info(test_data)

    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        import traceback
        traceback.print_exc()

    # 输出测试结果汇总
    logger.info("")
    logger.info("=" * 60)
    logger.info("Test Results Summary")
    logger.info("=" * 60)

    all_passed = True
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        logger.info(f"  {test_name}: {status}")
        if not passed:
            all_passed = False

    logger.info("")
    if all_passed:
        logger.success("All tests passed!")
    else:
        logger.warning("Some tests failed. Review the logs above for details.")

    logger.info("")
    logger.info("To clean up test data, run:")
    logger.info("  uv run python scripts/test_entity_semantic_search.py --cleanup")


if __name__ == "__main__":
    asyncio.run(main())
