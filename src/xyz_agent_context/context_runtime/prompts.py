"""
@file_name: prompts.py
@author: NetMind.AI
@date: 2025-12-22
@description: Prompt definitions for ContextRuntime
"""

# ============================================================================
# Auxiliary Narrative section header
# Used for Part 3 of build_complete_system_prompt()
# ============================================================================
AUXILIARY_NARRATIVES_HEADER = """
## Related Narratives (For Reference)
The following narratives are related to the current context and may provide useful background information.
You can reference them when relevant, but prioritize the main narrative above.
"""

# ============================================================================
# Module instructions section header
# Used for _build_module_instructions_prompt()
# ============================================================================
MODULE_INSTRUCTIONS_HEADER = """
## Module Instructions
The following are specific instructions from activated modules. Follow them as directed.
"""

# ============================================================================
# Short-term memory section header + description text
# Used for _build_short_term_memory_prompt() (2026-01-21 P1-2 dual-track memory)
# ============================================================================
SHORT_TERM_MEMORY_HEADER = """
## Short-Term Memory (Recent Other Topics)

The following are conversation snippets from **other topics you discussed with the user recently**. These may provide useful context but are not necessarily directly related to the current topic.

### Usage Guidelines
- **Prioritize conversation history (long-term memory)** to answer questions about the current topic
- Short-term memory is used for:
  - Understanding content the user just mentioned (even in other topics)
  - Maintaining conversation coherence (e.g., when the user says "like I just said...")
  - Avoiding repeatedly asking for information the user has already provided
- If information in short-term memory is unrelated to the current topic, it can be ignored

### Recent Conversation Snippets
"""
