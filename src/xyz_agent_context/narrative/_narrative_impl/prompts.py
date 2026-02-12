"""
@file_name: prompts.py
@author: NetMind.AI
@date: 2025-12-22
@description: Prompt definitions for the Narrative Prompt Builder
"""

# ============================================================================
# Narrative type descriptions
# Used in PromptBuilder.build_main_prompt() to select description text based on NarrativeType
# ============================================================================

# CHAT type description
NARRATIVE_TYPE_CHAT_PROMPT = "You are chatting with a user or an agent. Please make a good response to the user's request."

# TASK type description
NARRATIVE_TYPE_TASK_PROMPT = "You are performing a task. Please try your best to complete the task."

# GENERAL type description
NARRATIVE_TYPE_GENERAL_PROMPT = "You are performing a general things. Please complete it by yourself."

# ============================================================================
# Actor type descriptions
# Used in PromptBuilder.build_main_prompt() to select description text based on NarrativeActorType
# ============================================================================

# USER actor description
ACTOR_TYPE_USER_DESCRIPTION = "Creator/Owner - The user who created this Narrative"

# AGENT actor description
ACTOR_TYPE_AGENT_DESCRIPTION = "Agent - The AI Agent participating in this Narrative"

# PARTICIPANT actor description (2026-01-21 P2 new addition)
ACTOR_TYPE_PARTICIPANT_DESCRIPTION = "Participant - The target user of a Job, who can access this Narrative but is not the creator"

# SYSTEM actor description
ACTOR_TYPE_SYSTEM_DESCRIPTION = "System"

# ============================================================================
# Narrative main system prompt template
# Used in PromptBuilder.build_main_prompt() to assemble the final prompt
#
# Placeholder descriptions:
# - {narrative_id}: Narrative ID, from narrative.id
# - {type_prompt}: Narrative type description, from NARRATIVE_TYPE_*_PROMPT in this file
# - {created_at}: Creation time, from narrative.created_at
# - {updated_at}: Update time, from narrative.updated_at
# - {name}: Narrative name, from narrative.narrative_info.name
# - {description}: Narrative description, from narrative.narrative_info.description
# - {current_summary}: Current summary, from narrative.narrative_info.current_summary
# - {actor_prompt}: Actor list text, dynamically built by build_main_prompt()
# ============================================================================
# ============================================================================
# Continuity Detection - Narrative attribution judgment prompt
# Used in ContinuityDetector._call_llm()
# ============================================================================
CONTINUITY_DETECTION_INSTRUCTIONS = """You are a Narrative attribution analysis expert. Your task is to determine whether the user's current query belongs to the current Narrative.

**Key Concept**:
- Conversation continuity ≠ Same Narrative
- Users may switch to different topics/tasks during a continuous conversation, which requires creating a new Narrative

**8 Special Default Narratives (Important)**:
The system has 8 special default Narratives with simplified names and descriptions that require special handling:

1. **GreetingAndCourtesy**
   - Scope: Greetings, small talk, thanks, farewells, ending conversations - purely courteous exchanges
   - Characteristic: Does not carry any substantive topic; should switch once specific content is involved

2. **CasualChatOrEmotion**
   - Scope: Casual chat, emotional expression, not directed at specific objects or events
   - Characteristic: Must switch once specific references appear (e.g., "Python", "project")

3. **JokeAndEntertainment**
   - Scope: Pure entertainment requests, not involving any entities or ongoing topics
   - Characteristic: Entertainment-oriented, one-time interactions

4. **AgentHelpAndCapability**
   - Scope: Asking about the agent's features, usage, capability boundaries
   - Characteristic: Not related to specific business; meta-questions about the agent itself

5. **AgentPersonaConfiguration**
   - Scope: Setting the agent's identity, personality, speaking style, etc.
   - Characteristic: Configuration interactions that affect global behavior

6. **TaskLookup**
   - Scope: Viewing, searching, filtering task lists
   - Characteristic: Does not involve discussion of a specific task

7. **GeneralOneShotQuestion**
   - Scope: Independent, one-time questions (e.g., unit conversion, date lookup)
   - Characteristic: Will not generate ongoing discussion

8. **UnclassifiedOrGarbage**
   - Scope: Unclassifiable or meaningless input
   - Characteristic: Fallback container

**Rules for Special Default Narratives**:
- These Narratives have very strict boundaries; once the user mentions specific objects, tasks, or ongoing topics, it should be judged as **is_continuous = false**
- Example: Currently in "GreetingAndCourtesy", user says "help me write code" → must switch to new Narrative
- Example: Currently in "CasualChatOrEmotion", user says "Python decorators" → must switch to new Narrative

**Judgment Criteria**:

1. **Belongs to Current Narrative** → is_continuous = true
   - User is following up or diving deeper into the current Narrative's topic
   - User's question is solving the task/problem described in the current Narrative
   - User uses pronouns ("it", "this", "that") clearly referring to content in the current Narrative
   - User's new question is a continuation or extension of content within the current Narrative's scope
   - **Note**: For the 8 default Narratives, only questions that fully fit their narrow scope belong

2. **Does Not Belong to Current Narrative** → is_continuous = false
   - User raised a **completely different** new topic from the current Narrative's theme
   - User started a new, independent task/question
   - User explicitly indicates wanting to switch topics (e.g., "let's change the subject", "talk about something else")
   - Although conversation is continuous, the topic has jumped to another domain/task
   - **Note**: When switching from the 8 default Narratives to specific topics, must judge as not belonging

3. **Consider the Narrative's Core Theme** (if provided)
   - The Narrative's name and description define its thematic scope
   - The Narrative's summary reflects the conversation focus so far
   - Determine if the current query falls within this scope
   - **For the 8 default Narratives**: Prioritize judgment based on name, as summary info may be insufficient

4. **Consider the Agent's Response**
   - If the Agent's response introduced a new sub-topic and the user is following up, this still belongs to the same Narrative
   - If the Agent's response concluded a topic and the user starts a new one, it should be a new Narrative

5. **Time Factor**
   - If time elapsed is too long (e.g., over 10 minutes) and topic has changed, more likely to be a new Narrative

Output format:
- is_continuous: true (belongs to current Narrative) / false (should create new Narrative)
- confidence: 0.0-1.0 (confidence score)
- reason: Detailed reasoning explaining why it belongs or does not belong to the current Narrative
"""

# ============================================================================
# Single-Candidate Narrative Match - Single candidate matching prompt
# Used in NarrativeRetrieval._llm_confirm()
# ============================================================================
NARRATIVE_SINGLE_MATCH_INSTRUCTIONS = """You are a conversation topic matching expert. Analyze whether the user's new query relates to the given topic.

Requirements:
- You should thinking carefully and provide a detailed explanation of your reasoning.
- Try to use your logical reasoning ability to give the most reasonable judgment.

Output format:
class NarrativeMatchOutput(BaseModel):
    reason: str
    matched_index: int
    relation_type: RelationType
- reason: Detailed explanation of your reasoning
- matched_index: Index of the matched topic
- relation_type: Relation type: continuation, reference, other

Determine the relation_type:
- "continuation": The query directly continues, follows up, or deepens the existing topic
- "reference": The query uses pronouns (it, this, that) or indirect references to the topic
- "other": The query is unrelated to the topic. If none of the topics are related, return this.
"""

# ============================================================================
# Unified Narrative Match - Unified matching prompt (with PARTICIPANT branch)
# Used in NarrativeRetrieval._llm_judge_unified()
#
# Note: This prompt does not contain any scenario-specific logic (e.g., sales).
# The specific meaning of PARTICIPANT (sales target, collaborator, etc.) is defined by the Agent's Awareness.
# ============================================================================
NARRATIVE_UNIFIED_MATCH_WITH_PARTICIPANT_INSTRUCTIONS = """You are a conversation topic matching expert. You need to determine which category the user's new query should match:
1. Match a **participant-associated topic** (the user is a PARTICIPANT in these Narratives, prioritize matching)
2. Match a default topic type (generic scenarios like greetings, jokes, etc.)
3. Match an existing specific topic (a conversation topic already in the database)
4. Create a new topic (does not match any existing content)

**Important**: The current user is a PARTICIPANT in certain Narratives.
- If the user's message relates to the topic of a participant Narrative, prioritize matching the "participant" type
- If the user is simply greeting or chatting casually, it can still match the "default" type

Default topic types:
1. GreetingAndCourtesy: Greetings, small talk, thanks, farewells
2. CasualChatOrEmotion: Casual chat or emotional expression (no specific topic)
3. JokeAndEntertainment: Entertainment requests (e.g., tell a joke)
4. AgentHelpAndCapability: Asking about the Agent's features and capabilities
5. AgentPersonaConfiguration: Setting the Agent's persona or behavior style
6. TaskLookup: Viewing or searching task lists
7. GeneralOneShotQuestion: One-time general knowledge Q&A
8. UnclassifiedOrGarbage: Meaningless input or unclassifiable queries

Judgment priority:
1. **First check if it relates to a participant Narrative** (prioritize matching "participant")
2. If it's simple greetings/chat, match a default type
3. If it relates to an existing topic, match search results
4. If nothing matches, return create new topic

Requirements:
- Carefully analyze the user query's intent
- Provide detailed reasoning
- If matching a participant Narrative, return matched_category = "participant" with the corresponding index
- If matching a default type, return matched_category = "default" with the corresponding index
- If matching an existing topic, return matched_category = "search" with the corresponding index
- If nothing matches, return matched_category = "none"

Output format:
class UnifiedMatchOutput(BaseModel):
    reason: str  # Detailed reasoning process
    matched_category: str  # "participant", "default", "search", or "none"
    matched_index: int  # Matched index (0-based), -1 if matched_category="none"
"""

NARRATIVE_UNIFIED_MATCH_INSTRUCTIONS = """You are a conversation topic matching expert. You need to determine which category the user's new query should match:
1. Match a default topic type (generic scenarios like greetings, jokes, etc.)
2. Match an existing specific topic (a conversation topic already in the database)
3. Create a new topic (does not match any existing content)

Default topic types (match these first):
1. GreetingAndCourtesy: Greetings, small talk, thanks, farewells
2. CasualChatOrEmotion: Casual chat or emotional expression (no specific topic)
3. JokeAndEntertainment: Entertainment requests (e.g., tell a joke)
4. AgentHelpAndCapability: Asking about the Agent's features and capabilities
5. AgentPersonaConfiguration: Setting the Agent's persona or behavior style
6. TaskLookup: Viewing or searching task lists
7. GeneralOneShotQuestion: One-time general knowledge Q&A
8. UnclassifiedOrGarbage: Meaningless input or unclassifiable queries

Judgment priority:
1. First check if it matches a default topic type (if yes, return immediately without considering existing topics)
2. If it doesn't match a default type, check if it relates to an existing topic
3. If nothing matches, return create new topic

Requirements:
- Carefully analyze the user query's intent
- Provide detailed reasoning
- If matching a default type, return matched_category = "default" with the corresponding index
- If matching an existing topic, return matched_category = "search" with the corresponding index
- If nothing matches, return matched_category = "none"

Output format:
class UnifiedMatchOutput(BaseModel):
    reason: str  # Detailed reasoning process
    matched_category: str  # "default", "search", or "none"
    matched_index: int  # Matched index (0-based), -1 if matched_category="none"
"""

# ============================================================================
# Narrative Update - Narrative metadata incremental update prompt
# Used in NarrativeUpdater._call_llm_for_update()
# ============================================================================
NARRATIVE_UPDATE_INSTRUCTIONS = """You are a conversation analysis expert responsible for maintaining the metadata of conversation Narratives.

## Core Principle: Incremental Update
This is an **incremental update** task. You must:
- **Preserve and extend** existing information, not replace it
- **Combine** historically accumulated information + latest conversation content
- Information volume should be **increasing**; summaries should become more complete over time

## Task
Based on the **existing Narrative information** and the **latest conversation content**, update the following fields:

1. **name**: Short conversation topic name (3-10 words)
   - Summarize the core theme of the entire conversation
   - If the theme hasn't fundamentally changed, keep the original name
   - Only adjust when the conversation direction has clearly shifted

2. **current_summary**: Complete summary of the current conversation (50-200 words)
   - **Important**: **Append** new developments to the existing summary, do not rewrite
   - Include: historical topics + latest progress + key decisions/conclusions
   - Information should become richer over time, reflecting the complete conversation trajectory

3. **topic_keywords**: Topic keyword list (5-12 items)
   - **Retain** existing relevant keywords
   - **Add** key concepts from the new conversation
   - Keyword count should increase as the conversation deepens

4. **actors**: Conversation participant list
   - Include user (user), Agent (agent)
   - **Accumulate** important entities mentioned in the conversation (person names, project names, tool names, etc.)

5. **dynamic_summary_entry**: One-sentence summary of this conversation turn
   - Briefly summarize the core content of **this round** of conversation (one sentence)
   - This is an incremental entry for tracking conversation evolution

## Output Requirements
- Keep it concise and accurate
- Use original terms for technical terminology
- **Remember**: Extend on the existing basis, do not rewrite from scratch
"""

# ============================================================================
# Narrative main system prompt template
# Used in PromptBuilder.build_main_prompt() to assemble the final prompt
#
# Placeholder descriptions:
# - {narrative_id}: Narrative ID, from narrative.id
# - {type_prompt}: Narrative type description, from NARRATIVE_TYPE_*_PROMPT in this file
# - {created_at}: Creation time, from narrative.created_at
# - {updated_at}: Update time, from narrative.updated_at
# - {name}: Narrative name, from narrative.narrative_info.name
# - {description}: Narrative description, from narrative.narrative_info.description
# - {current_summary}: Current summary, from narrative.narrative_info.current_summary
# - {actor_prompt}: Actor list text, dynamically built by build_main_prompt()
# ============================================================================
NARRATIVE_MAIN_PROMPT_TEMPLATE = """
## Narrative System (Common Knowledge)

### What is a Narrative?
A Narrative is a context container for conversations/tasks, used for:
- Organizing related conversation history and task progress
- Maintaining participant (Actors) relationships
- Supporting cross-session continuity tracking

### Actor Types
| Type | Description | Permissions |
|------|-------------|-------------|
| **USER** | Creator/Owner of the Narrative | Full access, can create Jobs |
| **AGENT** | Participating AI Agent | Assists in executing tasks |
| **PARTICIPANT** | Target user of a Job | Can access this Narrative, but is not the creator |

### System Behavior
- When a user initiates a conversation, the system automatically matches or creates a Narrative
- When creating a Job, the target user (related_entity_id) is added as a PARTICIPANT
- When a PARTICIPANT converses with the Agent, the system loads the associated Narrative context

---

## Current Narrative Info

### Basic Metadata
- Narrative ID: {narrative_id}
- Narrative Type: {type_prompt}
- Created At: {created_at}
- Updated At: {updated_at}

### Narrative Details
- Name: {name}
- Description: {description}
- Current Summary: {current_summary}

### Actors (Participants)
{actor_prompt}

### Context Guidelines
1. Your reasoning, decisions, and actions must align with the narrative context at all times.
2. When interpreting user requests, prioritize consistency with the narrative's goals.
3. Use the narrative to maintain continuity across turns.
4. If the narrative contains ambiguities, resolve them through explicit reasoning.
5. Treat the narrative as persistent memory for this task environment.
"""
