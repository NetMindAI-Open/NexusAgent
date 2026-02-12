"""
@file_name: execution_state.py
@author: NetMind.AI
@date: 2025-11-28
@description: Agent execution state management

State management module extracted from AgentRuntime, responsible for tracking state during Agent Loop execution.

Design principles:
- Immutable design: each state update returns a new object for easy tracking and debugging
- Single responsibility: only responsible for state storage and updates, no business logic
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass(frozen=True)
class ExecutionState:
    """
    Agent execution state - immutable design

    Each update returns a new state object for easy tracking and debugging.

    Attributes:
        final_output: Final text output (cumulative)
        response_count: Total number of responses received
        tool_call_count: Number of tool calls
        thinking_count: Number of thinking processes
        all_steps: Records of all execution steps

    Usage:
        >>> state = ExecutionState()
        >>> state = state.append_text("Hello ")
        >>> state = state.append_text("World!")
        >>> print(state.final_output)  # "Hello World!"
    """
    final_output: str = ""
    response_count: int = 0
    tool_call_count: int = 0
    thinking_count: int = 0
    all_steps: tuple = field(default_factory=tuple)  # Use tuple for immutability

    def append_text(self, text: str) -> 'ExecutionState':
        """
        Append text output, returns a new state object

        Args:
            text: Text to append

        Returns:
            New ExecutionState object
        """
        return ExecutionState(
            final_output=self.final_output + text,
            response_count=self.response_count + 1,
            tool_call_count=self.tool_call_count,
            thinking_count=self.thinking_count,
            all_steps=self.all_steps,
        )

    def increment_response(self) -> 'ExecutionState':
        """
        Increment response count, returns a new state object

        Returns:
            New ExecutionState object
        """
        return ExecutionState(
            final_output=self.final_output,
            response_count=self.response_count + 1,
            tool_call_count=self.tool_call_count,
            thinking_count=self.thinking_count,
            all_steps=self.all_steps,
        )

    def record_tool_call(self, tool_name: str, tool_call_id: str, arguments: Dict[str, Any]) -> 'ExecutionState':
        """
        Record a tool call, returns a new state object

        Args:
            tool_name: Tool name
            tool_call_id: Tool call ID
            arguments: Tool arguments

        Returns:
            New ExecutionState object
        """
        new_step = {
            "type": "tool_call",
            "tool_name": tool_name,
            "tool_call_id": tool_call_id,
            "arguments": arguments,
        }
        return ExecutionState(
            final_output=self.final_output,
            response_count=self.response_count + 1,
            tool_call_count=self.tool_call_count + 1,
            thinking_count=self.thinking_count,
            all_steps=self.all_steps + (new_step,),
        )

    def record_tool_output(self, output: str) -> 'ExecutionState':
        """
        Record tool output, returns a new state object

        Args:
            output: Tool output content

        Returns:
            New ExecutionState object
        """
        new_step = {
            "type": "tool_output",
            "output": output,
        }
        return ExecutionState(
            final_output=self.final_output,
            response_count=self.response_count + 1,
            tool_call_count=self.tool_call_count,
            thinking_count=self.thinking_count,
            all_steps=self.all_steps + (new_step,),
        )

    def record_thinking(self, content: str) -> 'ExecutionState':
        """
        Record thinking process, returns a new state object

        Args:
            content: Thinking content

        Returns:
            New ExecutionState object
        """
        new_step = {
            "type": "thinking",
            "content": content,
        }
        return ExecutionState(
            final_output=self.final_output,
            response_count=self.response_count + 1,
            tool_call_count=self.tool_call_count,
            thinking_count=self.thinking_count + 1,
            all_steps=self.all_steps + (new_step,),
        )

    def finalize(self) -> 'ExecutionState':
        """
        Finalize execution, record final output to all_steps

        Returns:
            New ExecutionState object
        """
        if not self.final_output:
            return self

        final_step = {
            "type": "agent_final_output",
            "content": self.final_output,
            "length": len(self.final_output),
        }
        return ExecutionState(
            final_output=self.final_output,
            response_count=self.response_count,
            tool_call_count=self.tool_call_count,
            thinking_count=self.thinking_count,
            all_steps=self.all_steps + (final_step,),
        )

    def get_all_steps_as_list(self) -> List[Dict[str, Any]]:
        """
        Get all steps as a list (for serialization)

        Returns:
            List of steps
        """
        return list(self.all_steps)
