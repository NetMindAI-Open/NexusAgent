"""
@file_name: chat_module.py
@author: NetMind.AI
@date: 2025-11-15
@description: Chat Module - Provides chat-related functionality

ChatModule provides Agent messaging capabilities on the XYZ-Platform.

Core concept - Thinking vs Speaking:
- All output from Agent's LLM calls, Agent Loop, and tool calls are the Agent's internal thinking, invisible to users
- Only by calling the send_message_to_user_directly tool does the Agent actually "speak", and only then can users receive a response
- Like two people talking face-to-face: thinking in your head (invisible) vs speaking out loud (visible)

Included MCP Tools:
- send_message_to_user_directly: Agent speaks to user (real-time conversation, must be called for user to see response)
- agent_send_content_to_user_inbox: Agent proactively sends message to user's Inbox (async notification)
- agent_send_content_to_agent_inbox: Agent sends message to other Agents
- get_inbox_status: Get user Inbox status

Note: ChatModule itself does not include "multi-turn conversation" capability; multi-turn conversation requires Social-Network/Memory modules
"""


from typing import Optional, Any, List, Dict
from mcp.server.fastmcp import FastMCP
from loguru import logger


# Module (same package)
from xyz_agent_context.module import XYZBaseModule
from xyz_agent_context.module.event_memory_module import EventMemoryModule

# Schema
from xyz_agent_context.schema import (
    ContextData,
    HookAfterExecutionParams,
    ModuleConfig,
    MCPServerConfig,
    InboxMessageType,
)

# Utils
from xyz_agent_context.utils import DatabaseClient, utc_now

# Repository
from xyz_agent_context.repository import InboxRepository, AgentMessageRepository

# Schema
from xyz_agent_context.schema.agent_message_schema import MessageSourceType

# Prompts
from xyz_agent_context.module.chat_module.prompts import CHAT_MODULE_INSTRUCTIONS


class ChatModule(XYZBaseModule):
    """
    Chat Module - Core module for Agent-user communication

    Core concept - Thinking vs Speaking:
    Agent's internal processing (LLM calls, Agent Loop, tool calls) is like thinking in your head, completely invisible to users.
    Only through the send_message_to_user_directly tool can the Agent "speak", and only then can users receive the Agent's response.

    Provided capabilities:
    1. **Instructions** - Guide Agent to understand the "thinking vs speaking" distinction
    2. **Tools** (via MCP):
       - send_message_to_user_directly: Real-time response to user (must be called for user to see response)
       - agent_send_content_to_user_inbox: Async notification to Inbox
       - agent_send_content_to_agent_inbox: Inter-Agent communication
       - get_inbox_status: Query Inbox status
    3. **Data** - User's Inbox unread message count

    Dual-track memory loading (2026-01-21 P1-2):
    - Long-term memory: Current Narrative's EverMemOS semantically relevant history (2026-02-09 optimization)
    - Short-term memory: User's recent cross-Narrative conversations (most recent K messages, no time limit)
    """

    # Short-term memory configuration parameters (2026-02-09 optimization: removed time limit)
    SHORT_TERM_MAX_MESSAGES = 15    # Max short-term memory messages (most recent K across Narratives)
    # Note: Long-term memory count is controlled by EverMemOS retrieval top_k (see narrative/config.py)

    def __init__(
        self,
        agent_id: str,
        user_id: Optional[str] = None,
        database_client: Optional[DatabaseClient] = None,
        if_use_event_memory: bool = True,
        instance_id: Optional[str] = None,
        instance_ids: Optional[List[str]] = None
    ):
        super().__init__(agent_id, user_id, database_client, instance_id, instance_ids)

        if if_use_event_memory:
            self.event_memory_module = EventMemoryModule(agent_id, user_id, database_client)
        else:
            self.event_memory_module = None

        self.port = 7804  # MCP Server port (avoid conflict with SocialNetworkModule 7802)

        self.instructions = CHAT_MODULE_INSTRUCTIONS
        self.instance_ids = instance_ids    # TODO: Improve this capability in the future


    def get_config(self) -> ModuleConfig:
        """
        Return ChatModule configuration
        """
        return ModuleConfig(
            name="ChatModule",
            priority=1,  # High priority (base module)
            enabled=True,
            description="Provides messaging capabilities (instant chat + Inbox notifications)"
        )

    # ============================================================================= MCP Server

    async def get_mcp_config(self) -> Optional[MCPServerConfig]:
        """
        Return MCP Server configuration

        ChatModule provides MCP Server for:
        - agent_send_content_to_user_inbox: Agent proactively sends messages to users

        Returns:
            MCPServerConfig
        """
        return MCPServerConfig(
            server_name="chat_module",
            server_url=f"http://127.0.0.1:{self.port}/sse",
            type="sse"
        )

    def create_mcp_server(self) -> Optional[Any]:
        """
        Create MCP Server

        Provides the agent_send_content_to_user_inbox tool, enabling Agent to proactively send messages to users.
        """
        mcp = FastMCP("chat_module")
        mcp.settings.port = self.port

        @mcp.tool()
        async def agent_send_content_to_user_inbox(
            agent_id: str,
            user_id: str,
            title: str,
            content: str,
            event_id: str = ""
        ) -> str:
            """
            Send a message to the user's inbox.

            Use this tool when you want to proactively notify or communicate with the user.
            The message will appear in the user's inbox and they can read it later.

            Args:
                agent_id: Your agent ID (the sender).
                user_id: The user ID to send the message to.
                title: A brief, descriptive title for the message.
                content: The main content of the message.
                event_id: Optional event ID for tracking. Can be left empty.

            Returns:
                A confirmation message with the created message ID.

            Example:
                agent_send_content_to_user_inbox(
                    agent_id="agent_sales_001",
                    user_id="user_123",
                    title="Daily Summary",
                    content="Here's your daily summary: ..."
                )
            """
            # Use MCP-dedicated database connection
            db = await ChatModule.get_mcp_db_client()
            repo = InboxRepository(db)

            # source_type is fixed as "agent", source_id uses the passed-in agent_id
            actual_source_type = "agent"
            actual_source_id = agent_id

            # Message type is fixed as AGENT_MESSAGE
            message_type = InboxMessageType.AGENT_MESSAGE

            # Generate message_id
            from uuid import uuid4
            msg_id = f"msg_{uuid4().hex[:16]}"

            # Create message
            db_id = await repo.create_message(
                user_id=user_id,
                title=title,
                content=content,
                message_id=msg_id,
                message_type=message_type,
                source_type=actual_source_type,
                source_id=actual_source_id,
                event_id=event_id if event_id else None
            )

            logger.info(f"ChatModule: Sent message to user inbox - user={user_id}, title={title}, message_id={msg_id}")

            return f"Message sent successfully! Message ID: {msg_id}"

        @mcp.tool()
        async def agent_send_content_to_agent_inbox(target_agent_id: str, content: str, self_agent_id: str) -> str:
            """
            Send a message to another agent's inbox (agent_messages table).

            Use this tool when you want to communicate with another agent.
            The message will be stored in the target agent's message queue,
            and the target agent can process it later.

            Args:
                target_agent_id: The agent ID to send the message to (the receiver).
                content: The content of the message you want to send.
                self_agent_id: Your own agent ID (the sender).

            Returns:
                A confirmation message with the created message ID.

            Example:
                agent_send_content_to_agent_inbox(
                    target_agent_id="agent_456",
                    content="Please help me analyze this data...",
                    self_agent_id="agent_123"
                )
            """
            # Use MCP-dedicated database connection
            db = await ChatModule.get_mcp_db_client()
            repo = AgentMessageRepository(db)

            # Create message: source_type is agent, source_id is the sender's agent_id
            message_id = await repo.create_message(
                agent_id=target_agent_id,          # Agent the message belongs to (receiver)
                source_type=MessageSourceType.AGENT,  # Source type is agent
                source_id=self_agent_id,           # Source ID is the sender's agent_id
                content=content,
                if_response=False,                 # Initial state: not replied
                narrative_id=None,                 # Filled after Agent replies
                event_id=None,                     # Filled after Agent replies
            )

            logger.info(
                f"ChatModule: Sent message to agent inbox - "
                f"from={self_agent_id}, to={target_agent_id}, message_id={message_id}"
            )

            return f"Message sent successfully to agent {target_agent_id}! Message ID: {message_id}"

        @mcp.tool()
        async def get_inbox_status(user_id: str) -> str:
            """
            Get the inbox status for a user.

            Args:
                user_id: The user ID to check.

            Returns:
                A summary of the user's inbox status.
            """
            # Use MCP-dedicated database connection
            db = await ChatModule.get_mcp_db_client()
            repo = InboxRepository(db)

            unread_count = await repo.get_unread_count(user_id)

            if unread_count == 0:
                return f"User {user_id} has no unread messages in their inbox."

            # Get recent unread messages
            recent_messages = await repo.get_messages(user_id, is_read=False, limit=3)

            status = f"User {user_id} has {unread_count} unread message(s).\n\nRecent unread messages:\n"
            for msg in recent_messages:
                status += f"- [{msg.title}] {msg.content[:50]}...\n"

            return status
        
        @mcp.tool()
        async def get_chat_history(
            instance_id: str,
            limit: int = 20
        ) -> dict:
            """
            Get chat history for a specified Chat Instance.

            Each user has an independent Chat Instance within a Narrative, used to store that user's conversation history with the Agent.
            When a sales manager asks about interactions with a specific customer, this tool can be used to get that customer's complete chat history.
            Returned messages are sorted chronologically and contain both user and Agent conversation content.

            Args:
                instance_id: Chat Instance ID (format: chat_xxxxxxxx), used to locate a specific user's conversation
                limit: Maximum number of messages to return, default 20. Set to -1 to return all

            Returns:
                dict: Dictionary containing chat history, format:
                {
                    "success": True/False,
                    "instance_id": "chat_xxx",
                    "total_messages": 10,
                    "messages": [
                        {"role": "user", "content": "...", "timestamp": "..."},
                        {"role": "assistant", "content": "...", "timestamp": "..."},
                        ...
                    ]
                }

            Example:
                # Get conversation history with customer Alice
                # Assuming Alice's Chat Instance ID is "chat_abc12345"
                get_chat_history(
                    instance_id="chat_abc12345",
                    limit=10
                )
            """
            import json

            # Use MCP-dedicated database connection
            db = await ChatModule.get_mcp_db_client()

            # Query ChatModule's Instance-based JSON Format Memory table
            # Table name format: instance_json_format_memory_chat
            table_name = "instance_json_format_memory_chat"

            # Check if table exists
            check_query = """
                SELECT COUNT(*) as cnt
                FROM information_schema.tables
                WHERE table_schema = DATABASE()
                AND table_name = %s
            """
            result = await db.execute(check_query, params=(table_name,), fetch=True)
            table_exists = result and len(result) > 0 and result[0].get("cnt", 0) > 0

            if not table_exists:
                return {
                    "success": False,
                    "instance_id": instance_id,
                    "error": f"Chat history table {table_name} does not exist",
                    "total_messages": 0,
                    "messages": []
                }

            # Query chat history
            query = f"""
                SELECT `memory` FROM `{table_name}`
                WHERE `instance_id` = %s
            """

            try:
                result = await db.execute(query, params=(instance_id,), fetch=True)

                if not result or len(result) == 0 or not result[0].get("memory"):
                    return {
                        "success": True,
                        "instance_id": instance_id,
                        "total_messages": 0,
                        "messages": [],
                        "note": "This Chat Instance has no chat history yet"
                    }

                # Parse JSON format memory
                memory_str = result[0]["memory"]
                memory_data = json.loads(memory_str)
                messages = memory_data.get("messages", [])

                # Apply limit
                total_messages = len(messages)
                if limit > 0 and total_messages > limit:
                    # Return the most recent `limit` messages
                    messages = messages[-limit:]

                # Format output
                formatted_messages = []
                for msg in messages:
                    formatted_msg = {
                        "role": msg.get("role", "unknown"),
                        "content": msg.get("content", ""),
                    }
                    # Add metadata (if available)
                    if "meta_data" in msg:
                        meta = msg["meta_data"]
                        if "timestamp" in meta:
                            formatted_msg["timestamp"] = meta["timestamp"]
                        if "event_id" in meta:
                            formatted_msg["event_id"] = meta["event_id"]

                    formatted_messages.append(formatted_msg)

                return {
                    "success": True,
                    "instance_id": instance_id,
                    "total_messages": total_messages,
                    "returned_messages": len(formatted_messages),
                    "messages": formatted_messages
                }

            except json.JSONDecodeError as e:
                logger.error(f"ChatModule.get_chat_history: JSON parsing failed - {e}")
                return {
                    "success": False,
                    "instance_id": instance_id,
                    "error": f"Chat history data format error: {str(e)}",
                    "total_messages": 0,
                    "messages": []
                }
            except Exception as e:
                logger.error(f"ChatModule.get_chat_history: Query failed - {e}")
                return {
                    "success": False,
                    "instance_id": instance_id,
                    "error": f"Query failed: {str(e)}",
                    "total_messages": 0,
                    "messages": []
                }

        @mcp.tool()
        async def send_message_to_user_directly(agent_id: str, user_id: str, content: str) -> dict:
            """
            Speak to the user - This is the ONLY way to deliver your response to the user.

            **CRITICAL**: Think of this as "opening your mouth to speak". All your internal reasoning,
            tool calls, and agent loop outputs are like thoughts in your mind - completely invisible
            to the user. The user ONLY sees what you say through this tool.

            Analogy: Imagine you and the user are face-to-face:
            - Your LLM reasoning = thinking in your head (user cannot hear)
            - Your tool calls = actions you take silently (user cannot see)
            - Calling this tool = opening your mouth to speak (user CAN hear)

            Without calling this tool, your response stays in your head - the user receives NOTHING!

            Args:
                agent_id: Your agent ID (the speaker).
                user_id: The user ID you are speaking to (the listener).
                content: What you want to say to the user. This is the actual message
                         the user will see. Make it clear, helpful, and appropriate.
                         Which is in markdown format.

            Returns:
                A confirmation dict indicating the response was delivered successfully.

            Example:
                # After thinking and gathering information, speak to the user:
                send_message_to_user_directly(
                    agent_id="agent_123",
                    user_id="user_456",
                    content="Based on my analysis, here are the results you requested..."
                )
            """
            return {
                "success": True,
                "message": "Response delivered to user successfully",
                "user_id": user_id,
                "agent_id": agent_id,
                "content": content
            }

        return mcp


    # ============================================================================= Private Helper Methods

    async def _get_or_create_mcp_url(self) -> str:
        """
        Get or create MCP Server URL

        Returns:
            MCP Server URL
        """
        return f"http://127.0.0.1:{self.port}/sse"
    
    
    # ============================================================================= Hooks

    def _extract_user_visible_response(self, agent_loop_response: list) -> str:
        """
        Extract user-visible response content from agent_loop_response

        Iterates through agent_loop_response, looking for send_message_to_user_directly tool calls,
        and extracts the content parameter as the actual content displayed to the user.

        Logic is consistent with getUserVisibleResponse in the frontend chatStore.ts:
        - Tool name ends with 'send_message_to_user_directly' (Claude SDK format: mcp__chat_module__send_message_to_user_directly)
        - Extracts content field from tool_input/arguments

        Args:
            agent_loop_response: Raw response list from Agent Loop, containing ProgressMessage etc.

        Returns:
            str: User-visible response content; returns default message if send_message_to_user_directly was not called
        """
        from xyz_agent_context.schema import ProgressMessage

        for response in agent_loop_response:
            # Check if it's a ProgressMessage (tool calls are wrapped as ProgressMessage)
            if isinstance(response, ProgressMessage) and response.details:
                tool_name = response.details.get("tool_name", "")
                # Match send_message_to_user_directly (frontend uses endsWith matching)
                if tool_name.endswith("send_message_to_user_directly"):
                    arguments = response.details.get("arguments", {})
                    content = arguments.get("content", "")
                    if content:
                        logger.debug(
                            f"ChatModule._extract_user_visible_response: "
                            f"Extracted reply content from {tool_name}, length {len(content)}"
                        )
                        return content

        # send_message_to_user_directly call not found
        logger.debug(
            "ChatModule._extract_user_visible_response: "
            "send_message_to_user_directly tool call not found, Agent did not reply to user"
        )
        return "(Agent decided no response needed)"

    async def hook_data_gathering(self, ctx_data: ContextData) -> ContextData:
        """
        Data gathering phase - Dual-track memory loading (2026-01-21 P1-2)

        ChatModule in this phase:
        1. Load long-term memory: Current Narrative's ChatModule instance history
        2. Load short-term memory: User's recent conversations in other Narratives (most recent N minutes)
        3. Mark each message's memory_type (long_term / short_term)
        4. Fill merged conversation history into ctx_data.chat_history

        Args:
            ctx_data: ContextData, containing instance_id and instance_ids list

        Returns:
            ContextData: Context data with chat_history populated
        """
        module_name = self.config.name

        # Get the Instance ID list to query (long-term memory)
        # Prioritize self.instance_ids (set in AgentRuntime)
        current_instance_ids = []
        if self.instance_ids:
            current_instance_ids = self.instance_ids
            logger.debug(f"ChatModule.hook_data_gathering: Long-term memory Instance IDs: {len(current_instance_ids)}")
        elif self.instance_id:
            current_instance_ids = [self.instance_id]
            logger.debug(f"ChatModule.hook_data_gathering: Long-term memory single Instance ID: {self.instance_id}")

        if not current_instance_ids:
            logger.debug("ChatModule.hook_data_gathering: No instance_id, skipping history retrieval")
            ctx_data.chat_history = []
            return ctx_data

        # ========== 1. Load long-term memory (Current Narrative's EverMemOS semantically relevant history) ==========
        # 2026-02-09 optimization: Use EverMemOS episode_contents instead of full DB history
        long_term_messages = []
        current_narrative_id = ctx_data.narrative_id
        evermemos_memories = ctx_data.extra_data.get("evermemos_memories") if ctx_data.extra_data else None

        if evermemos_memories and current_narrative_id:
            # Priority path: Extract current Narrative's episode_contents from EverMemOS cache
            # Count is already controlled by EverMemOS retrieval top_k, no further limiting needed
            current_narrative_data = evermemos_memories.get(current_narrative_id)
            if current_narrative_data:
                episode_contents = current_narrative_data.get("episode_contents", [])
                topic_hint = current_narrative_data.get("topic_hint", "")

                for content in episode_contents:
                    # Directly use raw text format ("User: xxx\nAssistant: xxx")
                    long_term_messages.append({
                        "role": "context",  # Special role, indicates context from EverMemOS
                        "content": content,
                        "meta_data": {
                            "memory_type": "long_term",
                            "source": "evermemos",
                            "narrative_id": current_narrative_id,
                            "topic_hint": topic_hint,
                            "timestamp": ""  # EverMemOS has no timestamp
                        }
                    })

                logger.info(
                    f"ChatModule: Long-term memory - Retrieved {len(long_term_messages)} episodes from EverMemOS, "
                    f"topic_hint: {topic_hint}"
                )
                # Output preview of each episode content (for debugging)
                for i, content in enumerate(episode_contents):
                    # Truncate to first 500 characters as preview (for more complete viewing)
                    preview = content[:500].replace('\n', ' ')
                    if len(content) > 500:
                        preview += "..."
                    logger.debug(
                        f"ChatModule: Long-term memory [{i+1}/{len(episode_contents)}] (length {len(content)}): {preview}"
                    )
        else:
            # Fallback path: Load Instance conversation history from DB event_memory_module
            if self.event_memory_module:
                for instance_id in current_instance_ids:
                    memory = await self.event_memory_module.search_instance_json_format_memory(module_name, instance_id)

                    if memory and "messages" in memory:
                        messages = memory.get("messages", [])
                        for msg in messages:
                            if "meta_data" not in msg:
                                msg["meta_data"] = {}
                            msg["meta_data"]["instance_id"] = instance_id
                            msg["meta_data"]["memory_type"] = "long_term"

                            # Messages from non-chat sources (job/a2a): only load assistant side
                            working_source = msg.get("meta_data", {}).get("working_source", "chat")
                            if working_source != "chat" and msg.get("role") != "assistant":
                                continue

                            long_term_messages.append(msg)
                        logger.debug(
                            f"ChatModule: Long-term memory (DB fallback) - Instance {instance_id} retrieved {len(messages)} messages"
                        )
            else:
                logger.debug(
                    f"ChatModule: Long-term memory is empty - "
                    f"narrative_id={current_narrative_id}, "
                    f"evermemos_memories/event_memory_module both unavailable"
                )

        # Limit long-term memory count: keep only the most recent 20 conversation rounds (40 messages)
        MAX_LONG_TERM_ROUNDS = 20
        MAX_LONG_TERM_MESSAGES = MAX_LONG_TERM_ROUNDS * 2  # Each round = 1 user + 1 assistant
        if len(long_term_messages) > MAX_LONG_TERM_MESSAGES:
            original_count = len(long_term_messages)
            long_term_messages = long_term_messages[-MAX_LONG_TERM_MESSAGES:]
            logger.info(
                f"ChatModule: Long-term memory truncated - original {original_count} messages, kept most recent {MAX_LONG_TERM_MESSAGES}"
            )

        # ========== 2. Load short-term memory (recent cross-Narrative conversations) ==========
        short_term_messages = []
        if self.event_memory_module and self.agent_id and self.user_id:
            try:
                short_term_messages = await self._load_short_term_memory(
                    module_name=module_name,
                    exclude_instance_ids=current_instance_ids
                )
                if short_term_messages:
                    logger.debug(
                        f"ChatModule: Short-term memory - Retrieved {len(short_term_messages)} messages"
                    )
            except Exception as e:
                logger.warning(f"ChatModule: Short-term memory loading failed: {e}")

        # ========== 3. Merge and sort ==========
        all_messages = long_term_messages + short_term_messages

        if all_messages:
            def get_timestamp(msg):
                meta = msg.get("meta_data", {})
                timestamp = meta.get("timestamp", "")
                return timestamp if timestamp else "0000-00-00T00:00:00"

            all_messages.sort(key=get_timestamp)
            logger.info(
                f"ChatModule.hook_data_gathering: Dual-track loading complete - "
                f"long-term memory {len(long_term_messages)} messages, "
                f"short-term memory {len(short_term_messages)} messages, "
                f"total {len(all_messages)} messages"
            )
        else:
            logger.debug("ChatModule.hook_data_gathering: No history messages retrieved")

        # Fill merged history messages into ctx_data
        ctx_data.chat_history = all_messages
        return ctx_data

    async def _load_short_term_memory(
        self,
        module_name: str,
        exclude_instance_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Load short-term memory (recent cross-Narrative conversations) (2026-01-21 P1-2, 2026-02-09 optimization)

        Query user's ChatModule instances in other Narratives, get the most recent K messages (no time limit).

        Optimization notes (2026-02-09):
        - Removed 30-minute time window limit
        - Changed to return the most recent SHORT_TERM_MAX_MESSAGES messages
        - Reason: Time limit caused short-term memory to be empty for inactive users

        Args:
            module_name: Module name (used for querying memory table)
            exclude_instance_ids: Instance IDs to exclude (current Narrative's instances)

        Returns:
            Short-term memory message list (marked with memory_type="short_term")
        """
        from xyz_agent_context.utils.db_factory import get_db_client
        from xyz_agent_context.repository import InstanceRepository

        # Get all other ChatModule instances for the user
        db_client = await get_db_client()
        instance_repo = InstanceRepository(db_client)

        other_instances = await instance_repo.get_chat_instances_by_user(
            agent_id=self.agent_id,
            user_id=self.user_id,
            exclude_instance_ids=exclude_instance_ids
        )

        if not other_instances:
            logger.debug("ChatModule._load_short_term_memory: No other ChatModule instances")
            return []

        # Get messages from each instance (no longer time-limited)
        short_term_messages = []

        for instance in other_instances:
            memory = await self.event_memory_module.search_instance_json_format_memory(
                module_name, instance.instance_id
            )

            if not memory or "messages" not in memory:
                continue

            messages = memory.get("messages", [])

            # Collect all messages (no longer filtered by time)
            for msg in messages:
                meta = msg.get("meta_data", {})

                # Messages from non-chat sources (job/a2a): only load assistant side
                working_source = meta.get("working_source", "chat")
                if working_source != "chat" and msg.get("role") != "assistant":
                    continue

                # Mark as short-term memory
                if "meta_data" not in msg:
                    msg["meta_data"] = {}
                msg["meta_data"]["instance_id"] = instance.instance_id
                msg["meta_data"]["memory_type"] = "short_term"
                short_term_messages.append(msg)

        # Sort by time, limit count
        if short_term_messages:
            short_term_messages.sort(
                key=lambda m: m.get("meta_data", {}).get("timestamp", ""),
                reverse=True
            )
            # Take the most recent N messages
            short_term_messages = short_term_messages[:self.SHORT_TERM_MAX_MESSAGES]
            # Sort by time in ascending order again
            short_term_messages.sort(
                key=lambda m: m.get("meta_data", {}).get("timestamp", "")
            )

        logger.debug(
            f"ChatModule._load_short_term_memory: Retrieved "
            f"{len(short_term_messages)} short-term memory messages from {len(other_instances)} instances"
        )

        return short_term_messages

    async def hook_after_event_execution(self, params: HookAfterExecutionParams) -> None:
        """
        Post-event execution phase - Save conversation records to EventMemoryModule

        ChatModule in this phase:
        1. Append this conversation (input + output) to conversation history (stored by instance_id)
        2. Update Module status report (Report Memory) for Narrative orchestration use

        Note: assistant messages store the content parameter from the send_message_to_user_directly tool call,
        not final_output (Agent's thinking result). This ensures chat history displays the Agent's
        actual reply to the user, not the internal thinking process.

        Args:
            params: HookAfterExecutionParams, containing execution context, input/output, etc.
        """
        # Get necessary information
        instance_id = self.instance_id
        narrative_id = params.ctx_data.narrative_id if params.ctx_data else None
        module_name = self.config.name

        # If no instance_id or event_memory_module, skip
        if not instance_id or not self.event_memory_module:
            logger.debug(
                f"ChatModule.hook_after_event_execution: Missing necessary information, skipping "
                f"(instance_id={instance_id}, event_memory_module={self.event_memory_module is not None})"
            )
            return

        # ========== 1. Update conversation history (Instance-based JSON Format Memory) ==========
        # Get existing history (using instance_id)
        existing_memory = await self.event_memory_module.search_instance_json_format_memory(module_name, instance_id)
        messages = existing_memory.get("messages", []) if existing_memory else []

        # Append this conversation
        # Get working_source (execution source: chat/job/a2a)
        working_source = params.execution_ctx.working_source.value if params.execution_ctx else "unknown"

        # User message
        messages.append({
            "role": "user",
            "content": params.input_content,
            "meta_data": {
                "event_id": params.event_id,
                "timestamp": utc_now().isoformat(),
                "instance_id": instance_id,
                "working_source": working_source
            }
        })

        # Assistant message - Extract actual reply content from send_message_to_user_directly tool call
        # Instead of using final_output (which is the Agent's internal thinking result)
        assistant_content = self._extract_user_visible_response(params.agent_loop_response)

        messages.append({
            "role": "assistant",
            "content": assistant_content,
            "meta_data": {
                "event_id": params.event_id,
                "timestamp": utc_now().isoformat(),
                "instance_id": instance_id,
                "working_source": working_source
            }
        })

        # Save updated history (using instance_id)
        memory = {
            "messages": messages,
            "last_event_id": params.event_id,
            "updated_at": utc_now().isoformat()
        }
        await self.event_memory_module.add_instance_json_format_memory(module_name, instance_id, memory)

        logger.debug(
            f"ChatModule.hook_after_event_execution: Conversation record saved successfully, "
            f"instance_id={instance_id}, total messages={len(messages)}"
        )

        # ========== 2. Update status report (Report Memory) ==========
        # Generate status report for Narrative orchestration decision use
        # Note: Report Memory still uses narrative_id because it is a Narrative-level report
        if narrative_id:
            # TODO: This part may need additional LLM processing.
            total_rounds = len(messages) // 2  # Conversation rounds
            last_user_msg = params.input_content[:50] + "..." if len(params.input_content) > 50 else params.input_content
            # Use actual reply content (assistant_content) instead of final_output
            last_assistant_msg = assistant_content[:50] + "..." if len(assistant_content) > 50 else assistant_content

            report = (
                f"Conversation rounds: {total_rounds} | "
                f"Instance: {instance_id} | "
                f"Latest user message: {last_user_msg} | "
                f"Latest reply: {last_assistant_msg}"
            )

            await self.event_memory_module.update_report_memory(
                narrative_id=narrative_id,
                module_name=module_name,
                report_memory=report
            )

            logger.debug(
                f"ChatModule.hook_after_event_execution: Status report updated successfully, "
                f"narrative_id={narrative_id}, instance_id={instance_id}"
            )
        
        