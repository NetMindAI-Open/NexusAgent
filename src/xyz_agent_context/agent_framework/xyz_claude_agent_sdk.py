""" 
@file_name: xyz_claude_agent_sdk.py
@author: NetMind.AI
@date: 2025-11-15
@description: This file is the main file for the xyz claude agent sdk.
"""


from loguru import logger
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from typing import Any, AsyncGenerator

# Handle both relative import (when used as module) and absolute import (when run as script)
try:
    from .output_transfer import output_transfer
except ImportError:
    from output_transfer import output_transfer


class ClaudeAgentSDK:
    def __init__(self, working_path: str = "./"):
        self.working_path = working_path
    
    # TODO: Input is not ideal; should use a pydantic model for validation. Store it in src/xyz_agent_context/agent_framework/schema.py.
    async def agent_loop(
        self,
        messages: list[dict[str, Any]],
        mcp_server_urls: dict[str, str],  # Corrected type annotation: should be a dict, not a list
        streaming: bool = True,  # Whether to use streaming output
        **kwargs: Any,
        ) -> AsyncGenerator[dict[str, Any], None]:

        # Step 0-1: Convert mcp_server_urls to claude_agent_mcp_dict
        claude_agent_mcp_dict = {
            mcp_server_url[0]: {"type": "sse", "url": mcp_server_url[1]} for mcp_server_url in mcp_server_urls.items()
        }
        
        # Step 0-2: Build system prompt. Currently the Claude Agent SDK does not support multi-turn conversations,
        # so we need to manually append the conversation history to the system prompt.
        # Limit the maximum length of the system prompt to avoid "Argument list too long" errors.
        # Linux command-line argument limit is about 2MB, but the Claude SDK internally adds other arguments.
        # Use conservative settings to avoid "Argument list too long" errors.
        MAX_SYSTEM_PROMPT_LENGTH = 60000  # Approximately 60KB
        MAX_HISTORY_LENGTH = 30000  # Maximum history length 30KB

        system_prompt = ""
        for msg in messages:
            if msg["role"] == "system":
                system_prompt += msg["content"] + "\n"
        conversation_history = []
        user_messages = []
        this_turn_user_message = (messages.pop())["content"]    # TODO: Not robust enough; if the last message is not a user message, a logic error will occur. Needs adjustment.
        for i, msg in enumerate(messages):
            if msg["role"] == "user":
                user_messages.append(i)
                conversation_history.append(f"User: {msg['content']}")
            elif msg["role"] == "assistant":
                conversation_history.append(f"Assistant: {msg['content']}")
        # If there is conversation history, append it to the system prompt
        if len(user_messages) > 1:  # More than 1 user message indicates there is history
            history_text = "\n\n=== Chat History ===\n" + "\n\n".join(conversation_history)

            # If the history is too long, truncate and keep the most recent part
            if len(history_text) > MAX_HISTORY_LENGTH:
                logger.warning(f"Chat history too long ({len(history_text)} chars), truncating to {MAX_HISTORY_LENGTH} chars")
                # Keep the most recent history
                truncated_history = history_text[-MAX_HISTORY_LENGTH:]
                # Find the start of the first complete message
                first_user_idx = truncated_history.find("\nUser: ")
                first_assistant_idx = truncated_history.find("\nAssistant: ")
                if first_user_idx > 0 and (first_assistant_idx < 0 or first_user_idx < first_assistant_idx):
                    truncated_history = truncated_history[first_user_idx:]
                elif first_assistant_idx > 0:
                    truncated_history = truncated_history[first_assistant_idx:]
                history_text = "\n\n=== Chat History (truncated) ===\n" + truncated_history

            system_prompt += history_text
            system_prompt += "\n=== Chat History End ===\n These are the chat history between you and the user. This time please make the response by user input in this turn."

        # Final check on the total length of system_prompt
        if len(system_prompt) > MAX_SYSTEM_PROMPT_LENGTH:
            logger.warning(f"System prompt too long ({len(system_prompt)} chars), truncating to {MAX_SYSTEM_PROMPT_LENGTH} chars")
            system_prompt = system_prompt[:MAX_SYSTEM_PROMPT_LENGTH] + "\n\n[...truncated due to length limit...]"
                
        logger.debug(f"  System prompt length: {len(system_prompt):,} chars")
        logger.debug(f"  Your MCP: {claude_agent_mcp_dict}")
        # Step 1: Build ClaudeAgentOptions
        options = ClaudeAgentOptions(
            system_prompt=system_prompt,
            cwd=self.working_path, # TODO: Could pass the working directory via **kwargs; for now keep it simple - look for a folder in a directory, create one if it doesn't exist.
            mcp_servers=claude_agent_mcp_dict,
            permission_mode="bypassPermissions",
            max_buffer_size=50 * 1024 * 1024,  # 50MB buffer size for large MCP responses (PDF parsing etc.)
            include_partial_messages=True,  # Enable token-level streaming via StreamEvent
        )   # TODO: There are actually many more parameters available; see: https://docs.claude.com/en/docs/agent-sdk/python#message. These should be fully supported and passed through in the future.
        
        
        # Step 2: Create a ClaudeSDKClient instance, send the user message, and receive the response
        # TODO: The output adaptation may not be thorough enough and the display may not be ideal; needs more experimentation and design
        client = None
        try:
            client = ClaudeSDKClient(options=options)
            await client.connect()
            await client.query(this_turn_user_message)
            async for message in client.receive_response():
                yield output_transfer(message, transfer_type="claude_agent_sdk", streaming=streaming)
        except GeneratorExit:
            # Gracefully handle when the async generator is terminated early (e.g., user closes the connection)
            logger.warning("Agent loop generator was closed early (client disconnected)")
        except Exception as e:
            logger.error(f"Error in agent_loop: {e}")
            raise
        finally:
            # Manually disconnect to avoid task context issues with async with
            if client is not None:
                try:
                    await client.disconnect()
                except RuntimeError as e:
                    # Ignore "cancel scope in different task" errors
                    if "cancel scope" in str(e):
                        logger.debug(f"Ignoring cancel scope error during cleanup: {e}")
                    else:
                        raise
                except Exception as e:
                    logger.warning(f"Error during client disconnect: {e}")

