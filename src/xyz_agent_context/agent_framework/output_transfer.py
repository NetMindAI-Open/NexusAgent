"""
@file_name: output_transfer.py
@author: NetMind.AI
@date: 2025-11-15
@description: This file contains the output transfer functions to convert different agent SDK outputs to OpenAI Agents SDK format.
"""

from typing import Any, Dict


def output_transfer(
    message: Any,
    transfer_type: str = "claude_agent_sdk",
    streaming: bool = True
) -> Dict[str, Any]:
    """
    Transfer different agent SDK outputs to OpenAI Agents SDK format.

    Args:
        message: The message object from the agent SDK
        transfer_type: The type of transfer to perform (currently only "claude_agent_sdk" is supported)
        streaming: Whether to output streaming format (True) or non-streaming format (False)

    Returns:
        A dictionary in OpenAI Agents SDK event format
    """
    if transfer_type == "claude_agent_sdk":
        return _claude_to_openai_agents(message, streaming=streaming)
    else:
        raise ValueError(f"Unknown transfer type: {transfer_type}")


def _claude_to_openai_agents(message: Any, streaming: bool = True) -> Dict[str, Any]:
    """
    Convert Claude Agent SDK message to OpenAI Agents SDK format.

    Claude message types:
    - AssistantMessage: Contains Claude's response with content blocks (TextBlock, ThinkingBlock, ToolUseBlock)
    - UserMessage: User messages
    - SystemMessage: System messages
    - ResultMessage: Final result with cost information
    - StreamEvent: Streaming events with partial content

    OpenAI Agents SDK format (streaming):
    - raw_response_event: Contains ResponseTextDeltaEvent with delta field
    - run_item_stream_event: Contains items like tool_call_item, message_output_item, etc.
    - agent_updated_stream_event: Agent state updates

    OpenAI Agents SDK format (non-streaming):
    - RunResult-like structure with final_output and new_items
    """
    # Get message type name
    message_type = type(message).__name__

    if streaming:
        return _convert_to_streaming_event(message, message_type)
    else:
        return _convert_to_non_streaming_result(message, message_type)


def _convert_to_streaming_event(message: Any, message_type: str) -> Dict[str, Any]:
    """Convert Claude message to OpenAI Agents SDK streaming event format."""

    if message_type == "AssistantMessage":
        return _convert_assistant_to_stream_event(message)
    elif message_type == "StreamEvent":
        return _convert_stream_event_to_stream_event(message)
    elif message_type == "ResultMessage":
        return _convert_result_to_stream_event(message)
    elif message_type == "SystemMessage":
        return _convert_system_to_stream_event(message)
    elif message_type == "UserMessage":
        return _convert_user_to_stream_event(message)
    else:
        # Unknown message type
        return {
            "type": "raw_response_event",
            "data": {
                "type": "response.text.delta",
                "delta": f"[Unknown message type: {message_type}]"
            }
        }


def _convert_to_non_streaming_result(message: Any, message_type: str) -> Dict[str, Any]:
    """Convert Claude message to OpenAI Agents SDK non-streaming result format."""

    # For non-streaming, we accumulate all content and return a RunResult-like structure
    result = {
        "final_output": "",
        "new_items": [],
        "usage": {}
    }

    if message_type == "AssistantMessage":
        # Extract text content
        text_parts = []
        tool_calls = []

        if hasattr(message, 'content') and message.content:
            for block in message.content:
                block_type = type(block).__name__

                if block_type == "TextBlock" and hasattr(block, 'text'):
                    text_parts.append(block.text)
                    result["new_items"].append({
                        "type": "message_output_item",
                        "content": block.text
                    })
                elif block_type == "ThinkingBlock" and hasattr(block, 'thinking'):
                    # Optionally include thinking
                    result["new_items"].append({
                        "type": "thinking_item",
                        "content": block.thinking
                    })
                elif block_type == "ToolUseBlock":
                    if hasattr(block, 'id') and hasattr(block, 'name') and hasattr(block, 'input'):
                        tool_call = {
                            "type": "tool_call_item",
                            "tool_call_id": block.id,
                            "tool_name": block.name,
                            "arguments": block.input
                        }
                        tool_calls.append(tool_call)
                        result["new_items"].append(tool_call)

        result["final_output"] = "\n".join(text_parts) if text_parts else ""

    elif message_type == "ResultMessage":
        # Add usage information
        if hasattr(message, 'usage'):
            if hasattr(message.usage, 'input_tokens'):
                result["usage"]["input_tokens"] = message.usage.input_tokens
            if hasattr(message.usage, 'output_tokens'):
                result["usage"]["output_tokens"] = message.usage.output_tokens
            if result["usage"]:
                result["usage"]["total_tokens"] = (
                    result["usage"].get("input_tokens", 0) +
                    result["usage"].get("output_tokens", 0)
                )

        # Add stop reason
        if hasattr(message, 'stop_reason'):
            result["stop_reason"] = message.stop_reason

    return result


def _convert_assistant_to_stream_event(message: Any) -> Dict[str, Any]:
    """Convert Claude AssistantMessage to OpenAI Agents SDK stream event.

    With include_partial_messages=True, text and thinking content arrives twice:
    first via StreamEvents (token-by-token), then again in the complete AssistantMessage.
    To avoid duplication, we skip TextBlock and ThinkingBlock here (already streamed),
    and only emit ToolUseBlock events (needed for the Steps panel).
    """

    if not hasattr(message, 'content') or not message.content:
        return {
            "type": "raw_response_event",
            "data": {
                "type": "response.text.delta",
                "delta": ""
            }
        }

    # Iterate all blocks, skip Text/Thinking (already streamed), return first ToolUseBlock
    for block in message.content:
        block_type = type(block).__name__

        if block_type == "ToolUseBlock":
            if hasattr(block, 'id') and hasattr(block, 'name') and hasattr(block, 'input'):
                return {
                    "type": "run_item_stream_event",
                    "item": {
                        "type": "tool_call_item",
                        "tool_call_id": block.id,
                        "tool_name": block.name,
                        "arguments": block.input
                    }
                }

        # TextBlock, ThinkingBlock → skip (already streamed via StreamEvents)

    # No ToolUseBlock found; return empty delta (content already streamed)
    return {
        "type": "raw_response_event",
        "data": {
            "type": "response.text.delta",
            "delta": ""
        }
    }


def _convert_stream_event_to_stream_event(message: Any) -> Dict[str, Any]:
    """Convert Claude StreamEvent to OpenAI Agents SDK stream event.

    With include_partial_messages=True, StreamEvent carries an `event` dict
    containing Anthropic API streaming events (content_block_delta, etc.).
    We extract text and thinking deltas and forward them to the frontend.
    """

    event = getattr(message, 'event', None)
    if not isinstance(event, dict):
        # Fallback for unexpected format
        return {
            "type": "raw_response_event",
            "data": {
                "type": "response.text.delta",
                "delta": ""
            }
        }

    event_type = event.get("type", "")

    if event_type == "content_block_delta":
        delta = event.get("delta", {})
        delta_type = delta.get("type", "")

        if delta_type == "text_delta":
            return {
                "type": "raw_response_event",
                "data": {
                    "type": "response.text.delta",
                    "delta": delta.get("text", "")
                }
            }

        if delta_type == "thinking_delta":
            return {
                "type": "run_item_stream_event",
                "item": {
                    "type": "thinking_item",
                    "content": delta.get("thinking", "")
                }
            }

        # input_json_delta, signature_delta → skip (empty content)
        return {
            "type": "raw_response_event",
            "data": {
                "type": "response.text.delta",
                "delta": ""
            }
        }

    # Structural events (content_block_start/stop, message_start/delta/stop) → skip
    return {
        "type": "raw_response_event",
        "data": {
            "type": "response.text.delta",
            "delta": ""
        }
    }


def _convert_result_to_stream_event(message: Any) -> Dict[str, Any]:
    """Convert Claude ResultMessage to OpenAI Agents SDK stream event (completion marker)."""

    # Result message typically marks the end of the stream
    # We represent this as a raw_response_event with type "response.done"
    data = {
        "type": "response.done",
    }

    # Add usage info if available
    if hasattr(message, 'usage'):
        usage = {}
        if hasattr(message.usage, 'input_tokens'):
            usage["input_tokens"] = message.usage.input_tokens
        if hasattr(message.usage, 'output_tokens'):
            usage["output_tokens"] = message.usage.output_tokens
        if usage:
            usage["total_tokens"] = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
            data["usage"] = usage

    # Add stop reason
    if hasattr(message, 'stop_reason'):
        data["stop_reason"] = message.stop_reason

    return {
        "type": "raw_response_event",
        "data": data
    }


def _convert_system_to_stream_event(message: Any) -> Dict[str, Any]:
    """Convert Claude SystemMessage to OpenAI Agents SDK stream event."""

    content = ""
    if hasattr(message, 'metadata'):
        content = f"[System: {message.metadata}]"

    return {
        "type": "raw_response_event",
        "data": {
            "type": "response.text.delta",
            "delta": content
        }
    }


def _convert_user_to_stream_event(message: Any) -> Dict[str, Any]:
    """Convert Claude UserMessage to OpenAI Agents SDK stream event."""

    text_parts = []

    if hasattr(message, 'content') and message.content:
        for block in message.content:
            block_type = type(block).__name__

            if block_type == "TextBlock" and hasattr(block, 'text'):
                text_parts.append(block.text)
            elif block_type == "ToolResultBlock" and hasattr(block, 'content'):
                # Tool result
                return {
                    "type": "run_item_stream_event",
                    "item": {
                        "type": "tool_call_output_item",
                        "output": str(block.content)
                    }
                }

    content = "\n".join(text_parts) if text_parts else ""

    return {
        "type": "raw_response_event",
        "data": {
            "type": "response.text.delta",
            "delta": content
        }
    }
