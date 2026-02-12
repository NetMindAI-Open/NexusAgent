"""
@file_name: social_network_module.py
@author: NetMind.AI
@date: 2025-11-21
@description: Social Network Module - Provides social network recording and search capabilities

Per the design document:
- Social Network Module provides the ability to record and search interaction entities
- Contains: Instructions, Tools (MCP), Data (social_network_entities table), Hooks
- Core features:
  1. Record interaction entity information (identity, expertise, contact info)
  2. Intelligent social network search
  3. Automatically load relevant information at the right time
"""

from typing import Optional, Dict, Any, List
from loguru import logger
from datetime import datetime
from mcp.server.fastmcp import FastMCP

from pydantic import BaseModel, Field

# Module (same package)
from xyz_agent_context.module import XYZBaseModule
from xyz_agent_context.agent_framework.openai_agents_sdk import OpenAIAgentsSDK


# ===== LLM Output Schema Definitions =====

class SummaryOutput(BaseModel):
    """
    Conversation summary output structure
    """
    summary: str = Field(
        default="",
        description="Short summary of conversation key points (one line)"
    )


class CompressedDescriptionOutput(BaseModel):
    """
    Compressed description output structure
    """
    compressed_summary: str = Field(
        default="",
        description="Compressed description (no more than 500 characters)"
    )


class PersonaOutput(BaseModel):
    """
    Persona inference output structure
    """
    persona: str = Field(
        default="",
        description="Communication persona/style guide for interacting with this entity (1-3 sentences in natural language)"
    )


# Schema
from xyz_agent_context.schema import (
    ModuleConfig,
    MCPServerConfig,
    ContextData,
    ModuleInstructions,
    HookAfterExecutionParams,
)

# Utils
from xyz_agent_context.utils import DatabaseClient
from xyz_agent_context.utils.embedding import get_embedding

# Repository
from xyz_agent_context.repository import SocialNetworkRepository, SocialNetworkEntity, InstanceRepository

# Prompts
from xyz_agent_context.module.social_network_module.prompts import (
    SOCIAL_NETWORK_MODULE_INSTRUCTIONS,
    ENTITY_SUMMARY_INSTRUCTIONS,
    DESCRIPTION_COMPRESSION_INSTRUCTIONS,
    PERSONA_INFERENCE_INSTRUCTIONS,
)


class SocialNetworkModule(XYZBaseModule):
    """
    Social Network Module

    Provides social network capabilities:
    1. **Instructions** - Tells the Agent how to use social network features
    2. **Tools (MCP)** - Provides extract_entity_info, recall_entity, search_social_network tools
    3. **Data** - Stored in social_network_entities table
    4. **Hooks**:
       - hook_data_gathering: Load known information about the current interaction entity
       - hook_after_event_execution: Summarize and update entity information (Phase 2 implementation)
    """

    def __init__(
        self,
        agent_id: str,
        user_id: Optional[str] = None,
        database_client: Optional[DatabaseClient] = None,
        instance_id: Optional[str] = None,
        instance_ids: Optional[List[str]] = None
    ):
        super().__init__(agent_id, user_id, database_client, instance_id, instance_ids)
        self.port = 7802  # Use a different port to avoid conflict with awareness_module (7801)

        # Initialize repository (lazy initialization, since db may only be available at call time)
        self._social_repo: Optional[SocialNetworkRepository] = None

        # Build instructions, dynamically insert agent_id
        self.instructions = SOCIAL_NETWORK_MODULE_INSTRUCTIONS.replace("{agent_id}", agent_id)

    def _get_repo(self) -> SocialNetworkRepository:
        """Get or create SocialNetworkRepository instance"""
        if self._social_repo is None:
            self._social_repo = SocialNetworkRepository(self.db)
        return self._social_repo

    async def _get_instance_id(self) -> Optional[str]:
        """
        Get the current Module's instance_id

        Prefers self.instance_id; if None, looks up via agent_id + module_class.
        SocialNetworkModule is an Agent-level module (is_public=1), each Agent has only one instance.
        """
        if self.instance_id:
            return self.instance_id

        # Look up via agent_id + module_class
        try:
            instance_repo = InstanceRepository(self.db)
            instances = await instance_repo.get_by_agent(
                agent_id=self.agent_id,
                module_class="SocialNetworkModule"
            )
            if instances:
                self.instance_id = instances[0].instance_id
                return self.instance_id
        except Exception as e:
            logger.warning(f"Failed to get instance_id: {e}")

        return None

    def get_config(self) -> ModuleConfig:
        """
        Return SocialNetworkModule configuration
        """
        return ModuleConfig(
            name="SocialNetworkModule",
            priority=3,  # Medium priority
            enabled=True,
            description="Provides social network recording and search capabilities"
        )

    # ============================================================================= Hooks

    async def hook_data_gathering(self, ctx_data: ContextData) -> ContextData:
        """
        Load current interaction entity info when building context

        Functionality:
        1. Load known information for the current user_id
        2. Add information to ctx_data so the Agent knows "what I already know about the other party"
        3. Intent recognition (Phase 2): detect if other entities are mentioned or search is needed

        Refactoring notes (2025-12-24):
        - Uses instance_id to query instance_social_entities table
        - instance_id is obtained via _get_instance_id()

        Args:
            ctx_data: Context data

        Returns:
            Enriched ContextData
        """
        logger.debug(f"          → SocialNetworkModule.hook_data_gathering() started")

        try:
            # Get instance_id
            instance_id = await self._get_instance_id()
            if not instance_id:
                logger.warning("            No instance_id found, skipping social network data loading")
                ctx_data.social_network_current_entity = """**First time meeting this user.**

                    Remember to call `extract_entity_info` immediately when they introduce themselves or share personal information."""
                return ctx_data

            # 1. Load current interaction entity info
            if ctx_data.user_id:
                logger.debug(f"            Loading entity info for user_id: {ctx_data.user_id}, instance_id: {instance_id}")

                entity = await self._get_repo().get_entity(
                    entity_id=ctx_data.user_id,
                    instance_id=instance_id
                )

                if entity:
                    logger.debug(f"            ✓ Found entity: {entity.entity_name}")

                    # Add entity info to context
                    # This way the Agent can see this info in instructions
                    entity_info = {
                        "entity_id": entity.entity_id,
                        "entity_name": entity.entity_name,
                        "entity_description": entity.entity_description,
                        "identity_info": entity.identity_info or {},
                        "tags": entity.tags or [],
                        "interaction_count": entity.interaction_count,
                        "relationship_strength": entity.relationship_strength,
                        "last_interaction_time": entity.last_interaction_time.isoformat() if entity.last_interaction_time else None
                    }

                    # Format as readable display text
                    display_text = f"""**You already know this user:**
                        - Name: {entity.entity_name}
                        - Description: {entity.entity_description or 'N/A'}
                        - Tags: {', '.join(entity.tags) if entity.tags else 'None'}
                        - Previous interactions: {entity.interaction_count}
                        - Last contact: {entity.last_interaction_time.strftime('%Y-%m-%d') if entity.last_interaction_time else 'N/A'}

                        Use this information to provide personalized responses and build on previous conversations."""

                    # Inject Persona (if available)
                    if entity.persona:
                        display_text += f"""

**Communication Persona for {entity.entity_name}:**
{entity.persona}

Adapt your communication style according to this persona."""

                    ctx_data.social_network_current_entity = display_text
                    logger.info(f"            ✓ Loaded social network info for {entity.entity_name}")

                    # === Option C: Write related_job_ids to extra_data ===
                    # Allow JobModule to read and load Job context in subsequent hook_data_gathering
                    if entity.related_job_ids:
                        ctx_data.extra_data["related_job_ids"] = entity.related_job_ids
                        ctx_data.extra_data["current_entity_id"] = entity.entity_id
                        ctx_data.extra_data["current_entity_name"] = entity.entity_name
                        logger.info(f"            ✓ Wrote related_job_ids to extra_data: {entity.related_job_ids}")
                else:
                    logger.debug(f"            ℹ No existing entity info for {ctx_data.user_id}")
                    ctx_data.social_network_current_entity = """**First time meeting this user.**

                    Remember to call `extract_entity_info` immediately when they introduce themselves or share personal information."""
            else:
                # Case where user_id is empty (e.g., anonymous user or system call)
                logger.debug(f"            ℹ No user_id in ctx_data, skipping social network lookup")
                ctx_data.social_network_current_entity = """**No user context available.**

                    Social network features are available when interacting with identified users."""

            # 2. Intent recognition (Phase 2 implementation)
            # TODO: Detect if other entities are mentioned in input
            # TODO: Detect if expert search is needed

            logger.debug(f"          ← SocialNetworkModule.hook_data_gathering() completed")

        except Exception as e:
            logger.error(f"            ❌ Error in hook_data_gathering: {e}")
            logger.exception(e)
            # Set error state value to ensure get_instructions doesn't fail due to missing fields
            # Also clearly indicate an error occurred for debugging
            ctx_data.social_network_current_entity = f"""**⚠️ Social network data loading failed.**

Error: {type(e).__name__}: {str(e)[:100]}

Please check the database connection and ensure all required tables exist.
Run: `uv run python src/xyz_agent_context/utils/database_table_management/create_all_tables.py`"""

        return ctx_data

    async def hook_after_event_execution(self, params: HookAfterExecutionParams) -> None:
        """
        Automatically update entity_description after Event execution

        Functionality:
        1. Detect if the conversation contains identity information keywords
        2. If so, call LLM to summarize new information
        3. Append to entity_description (cumulative, not overwriting)
        4. Update interaction_count and last_interaction_time

        Division of responsibilities with extract_entity_info:
        - extract_entity_info: Actively called by Agent, updates structured info (tags, contact_info, identity_info)
        - hook_after_event_execution: Automatically executed, cumulatively updates natural language description (entity_description)

        Refactoring notes (2025-12-24):
        - Uses instance_id to query and update instance_social_entities table
        - instance_id is obtained via _get_instance_id()

        Args:
            params: HookAfterExecutionParams, containing:
                - execution_ctx: Execution context (event_id, agent_id, user_id, working_source)
                - io_data: Input/output (input_content, final_output)
                - trace: Execution trace (event_log, agent_loop_response)
                - ctx_data: Complete context data
        """
        logger.debug(f"          → SocialNetworkModule.hook_after_event_execution() started")

        try:
            # Get instance_id
            instance_id = await self._get_instance_id()
            if not instance_id:
                logger.warning("            No instance_id found, skipping hook")
                return

            # Get parameters (via convenience property access)
            user_id = params.user_id
            input_content = params.input_content
            final_output = params.final_output

            if not user_id:
                user_id = self.user_id

            if not user_id:
                logger.warning("            ⚠ No user_id found, skipping hook")
                return

            logger.debug(f"            Processing hook for user_id: {user_id}, instance_id: {instance_id}")

            # 0. Check if entity exists
            repo = self._get_repo()
            entity = await repo.get_entity(
                entity_id=user_id,
                instance_id=instance_id
            )

            # If entity does not exist, create a minimal entity
            # This way conversation history can be recorded even if the user hasn't introduced themselves
            if not entity:
                logger.info(f"            Entity {user_id} not found, creating minimal entity to record conversation")

                try:
                    await repo.add_entity(
                        entity_id=user_id,
                        entity_type="user",
                        instance_id=instance_id,
                        entity_name=user_id,  # Temporarily use user_id as name
                        entity_description="",  # Empty description, awaiting population
                        tags=[]  # Empty tags
                    )
                    logger.info(f"            ✓ Created minimal entity for {user_id}")
                except Exception as e:
                    logger.error(f"            ❌ Failed to create entity: {e}")
                    return

            # 1. Call LLM to summarize this round of conversation
            new_summary = await self._summarize_new_entity_info(input_content, final_output)

            if not new_summary or new_summary.strip() == "":
                logger.debug(f"            No new information to add")
                await self._update_interaction_stats(user_id, instance_id)
                return

            logger.info(f"            ✓ New summary generated: {new_summary[:100]}...")

            # 2. Append to entity_description
            await self._append_to_entity_description(user_id, instance_id, new_summary)

            # 3. Update embedding (based on latest entity_description + tags)
            await self._update_entity_embedding(user_id, instance_id)

            # 4. Update statistics
            await self._update_interaction_stats(user_id, instance_id)

            # 5. Check and update Persona (if needed)
            # Re-fetch entity to get the latest interaction_count
            entity = await repo.get_entity(entity_id=user_id, instance_id=instance_id)
            if entity and self._should_update_persona(entity, final_output):
                logger.info(f"            🎭 Updating persona for {user_id}...")

                # Get awareness and job_info (if available)
                awareness = ""
                job_info = ""
                if params.ctx_data:
                    # awareness may be in ctx_data's extra_data
                    awareness = getattr(params.ctx_data, 'awareness', '') or ''
                    # job_info may be in extra_data
                    if hasattr(params.ctx_data, 'extra_data') and params.ctx_data.extra_data:
                        related_jobs = params.ctx_data.extra_data.get('related_jobs_context', [])
                        if related_jobs:
                            job_info = str(related_jobs)

                # Build recent conversation
                recent_conversation = f"User: {input_content}\nAgent: {final_output}"

                # Infer new persona
                new_persona = await self._infer_persona(
                    entity=entity,
                    awareness=awareness,
                    job_info=job_info,
                    recent_conversation=recent_conversation
                )

                if new_persona:
                    await self._update_entity_persona(
                        entity_id=user_id,
                        instance_id=instance_id,
                        new_persona=new_persona
                    )

            logger.success(f"            ✅ Entity description updated for {user_id}")

        except Exception as e:
            logger.error(f"            ❌ Error in hook_after_event_execution: {e}")
            logger.exception(e)

        logger.debug(f"          ← SocialNetworkModule.hook_after_event_execution() completed")

    # ============================================================================= MCP Server

    async def get_mcp_config(self) -> Optional[MCPServerConfig]:
        """
        Return MCP Server configuration

        SocialNetworkModule needs to provide an MCP Server for:
        - extract_entity_info tool
        - recall_entity tool
        - search_social_network tool
        - get_contact_info tool

        Returns:
            MCPServerConfig
        """
        return MCPServerConfig(
            server_name="social_network_module",
            server_url=f"http://127.0.0.1:{self.port}/sse",
            type="sse"
        )

    def create_mcp_server(self) -> Optional[Any]:
        """
        Create MCP Server instance

        Provides the following tools:
        1. extract_entity_info - Extract and update entity information
        2. recall_entity - Recall information about a specific entity
        3. search_social_network - Search social network
        4. get_contact_info - Get contact information

        Returns:
            FastMCP instance
        """
        mcp = FastMCP("social_network_module")
        mcp.settings.port = self.port

        @mcp.tool()
        async def extract_entity_info(
            agent_id: str,
            entity_id: str,
            updates: dict | str,  # Supports dict or JSON string
            update_mode: str = "merge"
        ) -> dict:
            """
            IMMEDIATELY call this when someone introduces themselves or shares personal/professional information.

            Extract and persistently store information about users, agents, or organizations.
            This is how you build and maintain your social network memory with structured tags and identity data.

            **When to call (DO NOT WAIT)**:
            - User introduces themselves (name, role, company, expertise)
            - Someone mentions another person/agent/organization
            - Contact info is shared (email, phone, website)
            - Any biographical or professional detail appears

            Args:
                agent_id: The ID of the agent who owns this social network
                entity_id: The user_id or agent_id of the person
                updates: Information to update (entity_name, identity_info, contact_info, tags)
                     DO NOT include entity_description - it's auto-managed by conversation summaries
                update_mode: How to update: 'merge' combines with existing info, 'replace' overwrites (default: 'merge')

            Returns:
                Operation result with success status and message

            Example 1 - Expert level (EXPLICITLY claims expertise):
                User: "你好，我是Alice，我是推荐系统专家"

                extract_entity_info(
                    agent_id="your_agent_id",
                    entity_id="user_alice_123",
                    updates={
                        "entity_type": "user",
                        "entity_name": "Alice",
                        "tags": ["expert:推荐系统", "researcher"]
                    }
                )

            Example 2 - Familiar level (works with but doesn't claim expert):
                User: "我叫Bob，在Acme Corp做前端开发，主要用React"

                extract_entity_info(
                    agent_id="your_agent_id",
                    entity_id="user_bob_456",
                    updates={
                        "entity_type": "user",
                        "entity_name": "Bob",
                        "identity_info": {
                            "organization": "Acme Corp",
                            "position": "前端工程师",
                            "tech_stack": ["React"]
                        },
                        "tags": ["familiar:前端", "familiar:React", "engineer"]
                    }
                )

            Example 3 - Interested level (learning or exploring):
                User: "我最近在学NLP，对大模型很感兴趣"

                extract_entity_info(
                    agent_id="your_agent_id",
                    entity_id="user_carol_789",
                    updates={
                        "entity_type": "user",
                        "entity_name": "Carol",
                        "tags": ["interested:NLP", "interested:大模型", "student"]
                    }
                )


            Example 4 - Adding contact info:
                User: "我的邮箱是 alice@example.com"

                extract_entity_info(
                    agent_id="your_agent_id",
                    entity_id="user_alice_123",
                    updates={
                        "contact_info": {
                            "email": "alice@example.com"
                        }
                    },
                    update_mode="merge"  # Merges with existing info
                )
            """
            import json as _json

            # Process updates parameter: if it's a string, try to parse as dict
            if isinstance(updates, str):
                try:
                    updates = _json.loads(updates)
                except _json.JSONDecodeError as e:
                    return {
                        "success": False,
                        "message": f"Error: updates must be a valid JSON object, got string that failed to parse: {e}",
                        "entity_id": entity_id
                    }

            if not isinstance(updates, dict):
                return {
                    "success": False,
                    "message": f"Error: updates must be a dictionary, got {type(updates).__name__}",
                    "entity_id": entity_id
                }

            # Use MCP-dedicated database connection
            db = await SocialNetworkModule.get_mcp_db_client()

            # Find instance_id via agent_id + module_class
            instance_repo = InstanceRepository(db)
            instances = await instance_repo.get_by_agent(
                agent_id=agent_id,
                module_class="SocialNetworkModule"
            )

            if not instances:
                return {
                    "success": False,
                    "message": f"Error: No SocialNetworkModule instance found for agent_id={agent_id}"
                }

            instance_id = instances[0].instance_id

            # Create temporary module instance
            temp_module = SocialNetworkModule(agent_id=agent_id, database_client=db, instance_id=instance_id)
            result = await temp_module.extract_and_update_entity_info(
                entity_id=entity_id,
                instance_id=instance_id,
                updates=updates,
                update_mode=update_mode
            )
            return result

        @mcp.tool()
        async def search_social_network(
            agent_id: str,
            search_keyword: str,
            search_type: str = "auto",
            top_k: int = 5
        ) -> dict:
            """
            Search your social network for people. Supports exact lookup, tag search, and semantic search.

            Args:
                agent_id: The ID of the agent who owns this social network
                search_keyword: Can be:
                    - Exact entity_id: "user_alice_123", "entity_bob_456"
                    - Person's name: "Alice", "Bob"
                    - Tag: "expert:推荐系统", "architect", "familiar:机器学习"
                    - Natural language query (for semantic search): "谁最近表现出购买意向？"
                search_type: Type of search - 'auto' (recommended), 'exact_id', 'tags', 'semantic'
                    - 'auto': Automatically detects if it's an entity_id or tag/name
                    - 'exact_id': Force exact entity_id lookup
                    - 'tags': Search by tags only
                    - 'semantic': Natural language semantic search using embeddings
                top_k: Number of results to return (default: 5, ignored for exact_id)

            Returns:
                Search results with matching entities and their information (INCLUDING contact_info)
                For semantic search, results also include 'similarity_score' (0-1)

            Example 1 - Find specific person by entity_id:
                User: "Can you ask Alice about this?"

                search_social_network(
                    agent_id="your_agent_id",
                    search_keyword="user_alice_123",
                    search_type="auto"
                )
                # Returns exactly one person

            Example 2 - Find person by name:
                User: "Who is Bob?"

                search_social_network(
                    agent_id="your_agent_id",
                    search_keyword="Bob",
                    search_type="auto"
                )
                # Returns people with "Bob" in their name

            Example 3 - Find experts by tag:
                User: "你认识推荐系统专家吗？"

                search_social_network(
                    agent_id="your_agent_id",
                    search_keyword="expert:推荐系统",
                    search_type="tags",
                    top_k=5
                )

            Example 4 - Find by role:
                search_social_network(
                    agent_id="your_agent_id",
                    search_keyword="architect",
                    top_k=5
                )

            Example 5 - Semantic search (natural language):
                User: "谁最近表现出购买意向？"

                search_social_network(
                    agent_id="your_agent_id",
                    search_keyword="谁最近表现出购买意向？",
                    search_type="semantic",
                    top_k=5
                )
                # Returns people with [interested] signal in their description

            Example 6 - Find hesitating customers:
                search_social_network(
                    agent_id="your_agent_id",
                    search_keyword="which customers are hesitating or comparing alternatives",
                    search_type="semantic",
                    top_k=5
                )

            Note: Results include contact_info, so you usually don't need to call get_contact_info afterward.
            """
            # Use MCP-dedicated database connection
            db = await SocialNetworkModule.get_mcp_db_client()

            # Find instance_id via agent_id + module_class
            instance_repo = InstanceRepository(db)
            instances = await instance_repo.get_by_agent(
                agent_id=agent_id,
                module_class="SocialNetworkModule"
            )

            if not instances:
                return {
                    "success": False,
                    "message": f"Error: No SocialNetworkModule instance found for agent_id={agent_id}",
                    "results": []
                }

            instance_id = instances[0].instance_id

            temp_module = SocialNetworkModule(agent_id=agent_id, database_client=db, instance_id=instance_id)
            result = await temp_module.search_network(
                search_keyword=search_keyword,
                instance_id=instance_id,
                search_type=search_type,
                top_k=top_k
            )
            return result

        @mcp.tool()
        async def get_contact_info(agent_id: str, entity_id: str) -> dict:
            """
            Get contact information for reaching out to someone in your network.
            Use this when you need to know how to contact a specific person.

            Args:
                agent_id: The ID of the agent who owns this social network
                entity_id: The user_id or agent_id of the person

            Returns:
                Contact information including chat_channel, email, preferred_method, etc.
            """
            # Use MCP-dedicated database connection
            db = await SocialNetworkModule.get_mcp_db_client()

            # Find instance_id via agent_id + module_class
            instance_repo = InstanceRepository(db)
            instances = await instance_repo.get_by_agent(
                agent_id=agent_id,
                module_class="SocialNetworkModule"
            )

            if not instances:
                return {
                    "success": False,
                    "message": f"Error: No SocialNetworkModule instance found for agent_id={agent_id}"
                }

            instance_id = instances[0].instance_id

            temp_module = SocialNetworkModule(agent_id=agent_id, database_client=db, instance_id=instance_id)
            result = await temp_module.recall_entity_info(entity_id, instance_id)

            if result["success"]:
                entity = result["entity"]
                return {
                    "success": True,
                    "entity_id": entity_id,
                    "entity_name": entity.get("entity_name"),
                    "contact_info": entity.get("contact_info", {})
                }
            else:
                return {
                    "success": False,
                    "message": result["message"]
                }

        @mcp.tool()
        async def get_agent_social_stats(
            agent_id: str,
            sort_by: str = "recent",
            top_k: int = 5,
            filter_tags: str = ""
        ) -> dict:
            """
            View your social network from Agent's perspective - perfect for sales/outreach tracking!

            This tool lets you (the Agent's owner) ask questions like:
            - "Who did you contact recently?"
            - "Which customers engage with you most?"
            - "Show me your best relationships"

            Args:
                agent_id: The ID of the agent
                sort_by: How to sort results:
                    - "recent": Most recently contacted (best for "who did you talk to lately?")
                    - "frequent": Most interactions (best for "who engages most?")
                    - "strong": Strongest relationships (best for "your best contacts?")
                top_k: Number of results to return (default: 5)
                filter_tags: Optional comma-separated tags to filter (e.g., "expert:前端,architect")

            Returns:
                Sorted list with FULL entity info including:
                - entity_name, entity_description ← Key! Shows conversation summary
                - interaction_count, last_interaction_time
                - tags, contact_info, relationship_strength

            Example 1 - Sales Agent reporting recent contacts:
                User: "你最近联系了哪些潜在客户？情况怎么样？"

                get_agent_social_stats(
                    agent_id="sales_agent_001",
                    sort_by="recent",
                    top_k=5
                )

                Returns:
                {
                    "success": true,
                    "sort_by": "recent",
                    "count": 5,
                    "results": [
                        {
                            "entity_name": "Alice",
                            "entity_description": "Introduced as recommendation systems expert at Google.
                                                   Expressed interest in our real-time processing solution.
                                                   Said will discuss with team and get back next week.",
                            "interaction_count": 3,
                            "last_interaction_time": "2025-11-24T10:30:00",
                            "tags": ["expert:推荐系统", "architect"],
                            ...
                        },
                        ...
                    ]
                }

            Example 2 - Find most active customers:
                User: "哪些客户跟你互动最多？"

                get_agent_social_stats(
                    agent_id="sales_agent_001",
                    sort_by="frequent",
                    top_k=10
                )

            Example 3 - Check progress with frontend experts:
                User: "你联系的前端专家们进展如何？"

                get_agent_social_stats(
                    agent_id="sales_agent_001",
                    sort_by="recent",
                    filter_tags="expert:前端"
                )
            """
            # Use MCP-dedicated database connection
            db = await SocialNetworkModule.get_mcp_db_client()

            # Find instance_id via agent_id + module_class
            instance_repo = InstanceRepository(db)
            instances = await instance_repo.get_by_agent(
                agent_id=agent_id,
                module_class="SocialNetworkModule"
            )

            if not instances:
                return {
                    "success": False,
                    "message": f"Error: No SocialNetworkModule instance found for agent_id={agent_id}",
                    "results": []
                }

            instance_id = instances[0].instance_id

            temp_module = SocialNetworkModule(agent_id=agent_id, database_client=db, instance_id=instance_id)

            # Parse filter_tags
            filter_tags_list = None
            if filter_tags and filter_tags.strip():
                filter_tags_list = [tag.strip() for tag in filter_tags.split(",")]

            # Call helper method
            results = await temp_module._get_agent_stats(
                instance_id=instance_id,
                sort_by=sort_by,
                top_k=top_k,
                filter_tags=filter_tags_list
            )

            return {
                "success": True,
                "sort_by": sort_by,
                "count": len(results),
                "results": results
            }

        return mcp

    # ============================================================================= Helper Methods

    async def _load_entity_info(self, entity_id: str, instance_id: str) -> Optional[Dict[str, Any]]:
        """
        Load entity information (internal use)

        Args:
            entity_id: Entity ID
            instance_id: Instance ID

        Returns:
            Entity info dict or None
        """
        entity = await self._get_repo().get_entity(
            entity_id=entity_id,
            instance_id=instance_id
        )

        if not entity:
            return None

        return {
            "entity_id": entity.entity_id,
            "entity_name": entity.entity_name,
            "entity_description": entity.entity_description,
            "identity_info": entity.identity_info or {},
            "contact_info": entity.contact_info or {},
            "tags": entity.tags or [],
            "interaction_count": entity.interaction_count,
            "relationship_strength": entity.relationship_strength,
        }

    async def _search_entities(
        self,
        search_keyword: str,
        instance_id: str,
        search_type: str = "auto"
    ) -> List[Dict[str, Any]]:
        """
        Search entities (internal use)

        Args:
            search_keyword: Search keyword
            instance_id: Instance ID
            search_type: Search type (auto | exact_id | tags | semantic)

        Returns:
            List of matching entity information
        """
        # Auto: auto-detect type
        if search_type == "auto":
            # If starts with "user_" or "entity_", treat as entity_id
            if search_keyword.startswith(("user_", "entity_")):
                search_type = "exact_id"
            else:
                search_type = "tags"

        # Exact ID: exact lookup
        repo = self._get_repo()
        if search_type == "exact_id":
            entity = await repo.get_entity(
                entity_id=search_keyword,
                instance_id=instance_id
            )

            if entity:
                return [{
                    "entity_id": entity.entity_id,
                    "entity_name": entity.entity_name,
                    "entity_description": entity.entity_description,
                    "identity_info": entity.identity_info or {},
                    "tags": entity.tags or [],
                    "contact_info": entity.contact_info or {},
                    "relationship_strength": entity.relationship_strength,
                    "interaction_count": entity.interaction_count,
                }]
            else:
                return []

        # Tags: tag search
        if search_type == "tags":
            entities = await repo.search_by_tags(
                instance_id=instance_id,
                search_keyword=search_keyword
            )

            return [
                {
                    "entity_id": e.entity_id,
                    "entity_name": e.entity_name,
                    "entity_description": e.entity_description,
                    "tags": e.tags or [],
                    "contact_info": e.contact_info or {},
                    "relationship_strength": e.relationship_strength,
                }
                for e in entities
            ]

        # Semantic: semantic search (Feature 2.3)
        if search_type == "semantic":
            # Generate embedding for query text
            query_embedding = await get_embedding(search_keyword)

            # Execute semantic search
            results_with_scores = await repo.semantic_search(
                instance_id=instance_id,
                query_embedding=query_embedding,
                limit=10,  # Get more results, later limited by top_k
                min_similarity=0.3
            )

            return [
                {
                    "entity_id": e.entity_id,
                    "entity_name": e.entity_name,
                    "entity_description": e.entity_description,
                    "tags": e.tags or [],
                    "contact_info": e.contact_info or {},
                    "relationship_strength": e.relationship_strength,
                    "similarity_score": round(score, 3),  # Semantic similarity score
                }
                for e, score in results_with_scores
            ]

        return []

    async def _get_agent_stats(
        self,
        instance_id: str,
        sort_by: str = "recent",
        top_k: int = 10,
        filter_tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get Agent's social network statistics (internal use)

        Args:
            instance_id: Instance ID
            sort_by: Sort method (recent | frequent | strong)
            top_k: Number of results to return
            filter_tags: Tag filter

        Returns:
            Sorted entity list (with full info and description)
        """
        try:
            # Get all entities belonging to this Instance
            entities = await self._get_repo().get_all_entities(
                instance_id=instance_id,
                limit=1000  # Large enough limit
            )

            if not entities:
                return []

            # Filter by tags
            if filter_tags:
                entities = [
                    e for e in entities
                    if e.tags and any(tag in e.tags for tag in filter_tags)
                ]

            # Sort
            if sort_by == "recent":
                # Sort by last interaction time descending
                entities.sort(
                    key=lambda e: e.last_interaction_time or datetime.min,
                    reverse=True
                )
            elif sort_by == "frequent":
                # Sort by interaction count descending
                entities.sort(
                    key=lambda e: e.interaction_count,
                    reverse=True
                )
            elif sort_by == "strong":
                # Sort by relationship strength descending
                entities.sort(
                    key=lambda e: e.relationship_strength,
                    reverse=True
                )

            # Limit quantity
            entities = entities[:top_k]

            # Format return (including description!)
            return [
                {
                    "entity_id": e.entity_id,
                    "entity_name": e.entity_name,
                    "entity_description": e.entity_description or "No description yet",  # Key!
                    "last_interaction_time": e.last_interaction_time.isoformat() if e.last_interaction_time else None,
                }
                for e in entities
            ]

        except Exception as e:
            logger.error(f"Error getting agent stats: {e}")
            return []

    async def _update_interaction_stats(self, entity_id: str, instance_id: str) -> None:
        """
        Update interaction statistics (internal use)

        Args:
            entity_id: Entity ID
            instance_id: Instance ID
        """
        try:
            # Use repository's increment_interaction method, more efficient
            await self._get_repo().increment_interaction(
                entity_id=entity_id,
                instance_id=instance_id
            )
        except Exception as e:
            logger.error(f"Error updating interaction stats: {e}")

    async def _summarize_new_entity_info(self, input_content: str, final_output: str) -> str:
        """
        Call LLM to summarize key points of this round of conversation

        Args:
            input_content: User input
            final_output: Agent response

        Returns:
            Short summary of conversation key points
        """
        try:
            instructions = ENTITY_SUMMARY_INSTRUCTIONS

            user_input = f"""User: {input_content}
Agent: {final_output}

Summary (one line only):"""

            # Use OpenAIAgentsSDK's llm_function
            sdk = OpenAIAgentsSDK()
            result = await sdk.llm_function(
                instructions=instructions,
                user_input=user_input,
                output_type=SummaryOutput,
            )

            # result is RunResult, get parsed Pydantic object via .final_output
            output: SummaryOutput = result.final_output
            return output.summary.strip()

        except Exception as e:
            logger.error(f"Error summarizing entity info: {e}")
            return ""

    async def _append_to_entity_description(self, entity_id: str, instance_id: str, new_info: str) -> None:
        """
        Append information to entity_description (cumulative, not overwriting)

        Args:
            entity_id: Entity ID
            instance_id: Instance ID
            new_info: New information
        """
        try:
            # Get existing entity
            repo = self._get_repo()
            entity = await repo.get_entity(
                entity_id=entity_id,
                instance_id=instance_id
            )

            if not entity:
                logger.warning(f"Entity {entity_id} not found, cannot append description")
                return

            # Append information
            existing_desc = entity.entity_description or ""

            # If description already exists, append with separator
            if existing_desc:
                new_description = f"{existing_desc}\n- {new_info}"
            else:
                new_description = new_info

            # Check length, compress if exceeding threshold
            if len(new_description) > 2000:
                logger.info(f"Description too long ({len(new_description)} chars), compressing...")
                new_description = await self._compress_description(new_description)

            # Update database
            await repo.update_entity_info(
                entity_id=entity_id,
                instance_id=instance_id,
                updates={"entity_description": new_description}
            )

            logger.info(f"✓ Appended to entity_description: {new_info[:50]}...")

        except Exception as e:
            logger.error(f"Error appending to entity_description: {e}")

    async def _update_entity_embedding(self, entity_id: str, instance_id: str) -> None:
        """
        Update entity's embedding vector (based on entity_name + entity_description + tags)

        Args:
            entity_id: Entity ID
            instance_id: Instance ID
        """
        try:
            repo = self._get_repo()
            entity = await repo.get_entity(
                entity_id=entity_id,
                instance_id=instance_id
            )

            if not entity:
                logger.warning(f"Entity {entity_id} not found, cannot update embedding")
                return

            # Build text for embedding generation
            # Format: entity_name + entity_description + tags
            text_parts = []

            if entity.entity_name:
                text_parts.append(f"Name: {entity.entity_name}")

            if entity.entity_description:
                text_parts.append(f"Description: {entity.entity_description}")

            if entity.tags:
                text_parts.append(f"Tags: {', '.join(entity.tags)}")

            embedding_text = "\n".join(text_parts)

            if not embedding_text.strip():
                logger.debug(f"No content for embedding generation, skipping")
                return

            # Generate embedding
            embedding = await get_embedding(embedding_text)

            # Update database
            await repo.update_entity_info(
                entity_id=entity_id,
                instance_id=instance_id,
                updates={"embedding": embedding}
            )

            logger.info(f"✓ Updated embedding for entity {entity_id} (dim={len(embedding)})")

        except Exception as e:
            logger.error(f"Error updating entity embedding: {e}")

    async def _compress_description(self, long_description: str) -> str:
        """
        Compress overly long description (call LLM to re-summarize)

        Args:
            long_description: Overly long description

        Returns:
            Compressed description
        """
        try:
            instructions = DESCRIPTION_COMPRESSION_INSTRUCTIONS

            user_input = f"""{long_description}

Compressed summary:"""

            # Use OpenAIAgentsSDK's llm_function
            sdk = OpenAIAgentsSDK()
            result = await sdk.llm_function(
                instructions=instructions,
                user_input=user_input,
                output_type=CompressedDescriptionOutput,
            )

            # result is RunResult, get parsed Pydantic object via .final_output
            output: CompressedDescriptionOutput = result.final_output
            return output.compressed_summary.strip()

        except Exception as e:
            logger.error(f"Error compressing description: {e}")
            # If compression fails, at least truncate
            return long_description[:1000] + "..."

    # ============================================================================= Public API (for MCP Server)

    async def extract_and_update_entity_info(
        self,
        entity_id: str,
        instance_id: str,
        updates: Dict[str, Any],
        update_mode: str = "merge"
    ) -> Dict[str, Any]:
        """
        Extract and update entity information (called by MCP Server)

        Refactoring notes (2025-12-24):
        - Added instance_id parameter
        - Uses instance_id for data isolation

        Args:
            entity_id: Entity ID
            instance_id: Instance ID
            updates: Info dict to update
            update_mode: Update mode (merge | replace)

        Returns:
            Operation result
        """
        try:
            # Get existing entity
            repo = self._get_repo()
            existing_entity = await repo.get_entity(
                entity_id=entity_id,
                instance_id=instance_id
            )

            if existing_entity:
                # Merge update
                if update_mode == "merge":
                    # Merge identity_info
                    if "identity_info" in updates:
                        existing_info = existing_entity.identity_info or {}
                        new_info = updates["identity_info"]
                        merged_info = {**existing_info, **new_info}
                        updates["identity_info"] = merged_info

                    # Merge contact_info
                    if "contact_info" in updates:
                        existing_contact = existing_entity.contact_info or {}
                        new_contact = updates["contact_info"]
                        merged_contact = {**existing_contact, **new_contact}
                        updates["contact_info"] = merged_contact

                    # Merge tags (deduplicate)
                    if "tags" in updates:
                        existing_tags = set(existing_entity.tags or [])
                        new_tags = set(updates["tags"])
                        updates["tags"] = list(existing_tags | new_tags)

                    # Protect entity_description: not allowed to update via this function
                    # entity_description should only be cumulatively updated by hook_after_event_execution
                    if "entity_description" in updates:
                        logger.warning(
                            f"Attempted to update entity_description via extract_entity_info. "
                            f"This field is managed by hook_after_event_execution only. Ignoring."
                        )
                        updates.pop("entity_description")

                # Update
                await repo.update_entity_info(
                    entity_id=entity_id,
                    instance_id=instance_id,
                    updates=updates
                )

                return {
                    "success": True,
                    "message": "Entity info updated successfully",
                    "entity_id": entity_id
                }

            else:
                # Create new entity
                entity_type = updates.pop("entity_type", "user")
                entity_name = updates.pop("entity_name", None)
                # Ignore entity_description, managed only by hook
                if "entity_description" in updates:
                    logger.warning(
                        f"Ignoring entity_description in updates during entity creation. "
                        f"This field is managed by hook_after_event_execution only."
                    )
                    updates.pop("entity_description")

                identity_info = updates.pop("identity_info", {})
                contact_info = updates.pop("contact_info", {})
                tags = updates.pop("tags", [])

                await repo.add_entity(
                    entity_id=entity_id,
                    entity_type=entity_type,
                    instance_id=instance_id,
                    entity_name=entity_name,
                    entity_description="",  # Empty description, awaiting hook population
                    identity_info=identity_info,
                    contact_info=contact_info,
                    tags=tags
                )

                return {
                    "success": True,
                    "message": "New entity created successfully",
                    "entity_id": entity_id
                }

        except Exception as e:
            logger.error(f"Error in extract_and_update_entity_info: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "entity_id": entity_id
            }

    async def recall_entity_info(self, entity_id: str, instance_id: str) -> Dict[str, Any]:
        """
        Recall entity information (called by MCP Server)

        Refactoring notes (2025-12-24):
        - Added instance_id parameter
        - Uses instance_id for data isolation

        Args:
            entity_id: Entity ID
            instance_id: Instance ID

        Returns:
            Entity info or error message
        """
        try:
            entity_info = await self._load_entity_info(entity_id, instance_id)

            if entity_info:
                return {
                    "success": True,
                    "entity": entity_info
                }
            else:
                return {
                    "success": False,
                    "message": f"No information found for entity: {entity_id}"
                }

        except Exception as e:
            logger.error(f"Error in recall_entity_info: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}"
            }

    async def search_network(
        self,
        search_keyword: str,
        instance_id: str,
        search_type: str = "auto",
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Search social network (called by MCP Server)

        Refactoring notes (2025-12-24):
        - Added instance_id parameter
        - Uses instance_id for data isolation

        Args:
            search_keyword: Search keyword (entity_id, name, or tag)
            instance_id: Instance ID
            search_type: Search type (auto | exact_id | tags | semantic)
            top_k: Number of results to return (ignored for exact_id)

        Returns:
            Search results
        """
        try:
            entities = await self._search_entities(search_keyword, instance_id, search_type)

            # Limit return count (exact_id already returns only 1, no limit needed)
            if search_type != "exact_id":
                entities = entities[:top_k]

            return {
                "success": True,
                "search_keyword": search_keyword,
                "search_type": search_type,
                "results": entities,
                "count": len(entities)
            }

        except Exception as e:
            logger.error(f"Error in search_network: {e}")
            return {
                "success": False,
                "message": f"Error: {str(e)}",
                "results": []
            }

    # ============================================================================= Persona Methods

    def _should_update_persona(
        self,
        entity: SocialNetworkEntity,
        response_content: str = ""
    ) -> bool:
        """
        Determine if Persona needs to be updated

        Update conditions (triggered if any is met):
        1. First interaction (persona is empty)
        2. Forced re-evaluation every 10 conversation rounds
        3. Significant change signal detected in conversation

        Args:
            entity: SocialNetworkEntity entity
            response_content: Conversation content (for detecting change signals)

        Returns:
            bool: Whether Persona needs to be updated
        """
        # 1. First interaction, must initialize
        if entity.persona is None:
            logger.debug("            Persona update needed: first interaction (persona is None)")
            return True

        # 2. Forced re-evaluation every 10 rounds
        if entity.interaction_count > 0 and entity.interaction_count % 10 == 0:
            logger.debug(f"            Persona update needed: periodic re-evaluation (turn {entity.interaction_count})")
            return True

        # 3. Detect if there are significant change signals in the conversation
        # Note: signals should be lowercase since we compare with response_content.lower()
        change_signals = [
            "i changed my mind", "actually i care more about", "budget changed", "decision process changed",
            "change my mind", "our needs changed", "our requirements changed"
        ]
        if response_content and any(signal in response_content.lower() for signal in change_signals):
            logger.debug("            Persona update needed: change signal detected in conversation")
            return True

        return False

    async def _infer_persona(
        self,
        entity: SocialNetworkEntity,
        awareness: str = "",
        job_info: str = "",
        recent_conversation: str = ""
    ) -> str:
        """
        Infer Persona using LLM

        Args:
            entity: SocialNetworkEntity entity
            awareness: Agent's awareness (Master's guidance)
            job_info: Related Job information
            recent_conversation: Recent conversation content

        Returns:
            str: Inferred Persona description
        """
        try:
            instructions = PERSONA_INFERENCE_INSTRUCTIONS

            # Build entity info
            entity_context = f"""Contact Information:
- Name: {entity.entity_name or 'Unknown'}
- Type: {entity.entity_type}
- Description: {entity.entity_description or 'No description yet'}
- Tags: {', '.join(entity.tags) if entity.tags else 'None'}
- Interaction count: {entity.interaction_count}"""

            if entity.identity_info:
                entity_context += f"\n- Identity info: {entity.identity_info}"

            # Build user input
            user_input_parts = [entity_context]

            if awareness:
                user_input_parts.append(f"\nAgent Awareness (Master's Instructions):\n{awareness}")

            if job_info:
                user_input_parts.append(f"\nRelated Job Information:\n{job_info}")

            if recent_conversation:
                user_input_parts.append(f"\nRecent Conversation:\n{recent_conversation}")

            # If persona already exists, provide as reference
            if entity.persona:
                user_input_parts.append(f"\nCurrent Persona (for reference):\n{entity.persona}")

            user_input_parts.append("\nGenerate a concise communication persona for this contact:")

            user_input = "\n".join(user_input_parts)

            # Call LLM
            sdk = OpenAIAgentsSDK()
            result = await sdk.llm_function(
                instructions=instructions,
                user_input=user_input,
                output_type=PersonaOutput,
            )

            output: PersonaOutput = result.final_output
            persona = output.persona.strip()

            if persona:
                logger.info(f"            ✓ Persona inferred: {persona[:50]}...")
                return persona
            else:
                logger.warning("            ⚠ LLM returned empty persona")
                return entity.persona or ""

        except Exception as e:
            logger.error(f"            ❌ Error inferring persona: {e}")
            return entity.persona or ""

    async def _update_entity_persona(
        self,
        entity_id: str,
        instance_id: str,
        new_persona: str
    ) -> None:
        """
        Update entity's Persona

        Args:
            entity_id: Entity ID
            instance_id: Instance ID
            new_persona: New Persona
        """
        try:
            repo = self._get_repo()

            # Update database
            await repo.update_entity_info(
                entity_id=entity_id,
                instance_id=instance_id,
                updates={"persona": new_persona}
            )

            logger.info(f"            ✓ Entity persona updated")

        except Exception as e:
            logger.error(f"            ❌ Error updating entity persona: {e}")
