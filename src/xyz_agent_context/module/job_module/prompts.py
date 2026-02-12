"""
@file_name: prompts.py
@author: NetMind.AI
@date: 2025-11-25
@description: JobModule (JobTrigger) prompt definitions
"""

# ============================================================================
# Task info section template
# Used for the task info part of _build_execution_prompt()
#
# Placeholder description:
# - {title}: Job title, from job.title
# - {description}: Job description, from job.description
# - {created_str}: Creation time (formatted), from job.created_at
# - {current_time_str}: Current time (formatted)
# - {execution_user_id}: Execution identity user_id
# - {user_id}: Task creator user_id, from job.user_id
# ============================================================================
JOB_TASK_INFO_TEMPLATE = """## Task Information
- **Title**: {title}
- **Description**: {description}
- **Created at**: {created_str}
- **Current time**: {current_time_str}
- **Execution identity (user_id)**: {execution_user_id}
- **Task creator**: {user_id}"""

# ============================================================================
# Related entities section template
# Used in _build_execution_prompt() when entities_info exists
#
# Placeholder description:
# - {entity_lines}: Formatted entity info lines, dynamically built by _build_execution_prompt()
# ============================================================================
JOB_ENTITIES_SECTION_TEMPLATE = """
## Related People/Entities

{entity_lines}
"""

# ============================================================================
# Current progress section template
# Used in _build_execution_prompt() when narrative_summary exists
#
# Placeholder description:
# - {narrative_summary}: Narrative summary
# ============================================================================
JOB_PROGRESS_SECTION_TEMPLATE = """
## Current Progress

{narrative_summary}
"""

# ============================================================================
# Dependency section template
# Used in _build_execution_prompt() when dependent Job outputs exist
#
# Placeholder description:
# - {dep_parts}: Formatted dependency task outputs, dynamically built by _build_execution_prompt()
# ============================================================================
JOB_DEPENDENCIES_SECTION_TEMPLATE = """
## Prerequisite Task Results

The following are the execution results of prerequisite tasks this task depends on. Please refer to this information when executing this task:

{dep_parts}
---
"""

# ============================================================================
# Job execution main prompt template
# Used by _build_execution_prompt() to assemble the final prompt
#
# Placeholder description:
# - {task_info_section}: Task info section, formatted by JOB_TASK_INFO_TEMPLATE
# - {entities_section}: Related entities section, can be empty string
# - {narrative_section}: Current progress section, can be empty string
# - {dependency_section}: Dependency section, can be empty string
# - {payload}: Execution instructions, from job.payload
# - {related_entity_id}: Target user ID, from job.related_entity_id
# - {extra_requirement}: Extra requirement line (when context info exists), can be empty string
# ============================================================================
JOB_EXECUTION_PROMPT_TEMPLATE = """You are executing a background scheduled task. This is an asynchronous task. The user is not online right now and cannot see your real-time output, but you can still send them a message for them to check later.

{task_info_section}
{entities_section}
{narrative_section}
{dependency_section}
## Execution Instructions
{payload}

## Now you are facing to the target user: {related_entity_id}
If you want to send a message to the target user, you can use the chat mcp tool 'make_response_to_user'

## Important Requirements
1. Complete all steps required for the task (search, analyze, organize, etc.)
2. **After completing the task, you MUST use the `agent_send_content_to_user_inbox` tool to send the final report to the user**
3. The content sent should be the final report for the user, do not include the thinking process
4. The content should be complete, valuable, and clearly formatted (use Markdown)
5. Do not use make_response_to_user, because the user is not online
{extra_requirement}

Remember:
1. Using agent_send_content_to_user_inbox means you send a one-time message notification to the user.
2. Using end_message_to_user_directly means you send the message directly to the conversation between you and the user.
3. The two are slightly different, please choose the appropriate one. 1. is better for one-time message notifications; 2. is better for scenarios requiring multi-turn conversations.
"""
