"""
@file_name: module_schema.py
@author: NetMind.AI
@date: 2025-11-15
@description: Module related data models

Includes:
- ModuleConfig - Module configuration
- MCPServerConfig - MCP Server configuration
- ModuleInstructions - Module instructions
- ModuleInstance - Module instance serialization representation
- InstanceStatus - Re-exported from instance_schema for backward compatibility
"""

from enum import Enum
from typing import Optional, Dict, Any, List, TYPE_CHECKING
from datetime import datetime
from pydantic import BaseModel, Field

# InstanceStatus is uniformly imported from instance_schema
# This re-export is retained for backward compatibility (other files may import from here)
from xyz_agent_context.schema.instance_schema import InstanceStatus

if TYPE_CHECKING:
    from xyz_agent_context.module import XYZBaseModule


class ModuleConfig(BaseModel):
    """
    Module configuration

    Defines the basic configuration information for a Module

    module_type field description:
    - "capability": Capability module, auto-loaded via rules, no LLM judgment needed
      e.g., ChatModule, AwarenessModule, SocialNetworkModule, etc.
    - "task": Task module, requires LLM judgment for creation
      e.g., JobModule
    """
    name: str  # Module name
    priority: int  # Priority (for sorting instructions)
    enabled: bool = True  # Whether enabled
    description: str = ""  # Module description
    module_type: str = "capability"  # Module type: "capability" or "task"


class MCPServerConfig(BaseModel):
    """
    MCP Server configuration

    If a Module needs to provide an MCP Server, return this configuration
    """
    server_name: str  # Server name (e.g., "chat_history")
    server_url: str  # Server URL (e.g., "http://localhost:8000/chat/sse")
    type: str = "sse"  # Server type (default sse)


class ModuleInstructions(BaseModel):
    """
    Instruction information provided by the Module

    Will be added to the system prompt
    """
    name: str  # Module name
    instruction: str  # Specific instruction content
    priority: int  # Priority (for sorting)


# InstanceStatus has been moved to instance_schema.py, re-exported from the top


class ModuleInstance(BaseModel):
    """
    Module Instance - Runtime instance of a Module

    Design philosophy (refer to Agent Architecture Framework.md):
    - Instance belongs to Agent, managed by Narrative
    - Instance has independent ID, responsibilities, status, and Memory
    - Different Modules may manage instances differently

    Usage scenarios:
    - ChatModule: One Narrative typically has one instance (e.g., "chat_a1b2c3d4")
    - JobModule: One task corresponds to one instance (e.g., "job_e5f6g7h8")
    - SocialNetworkModule: One Narrative may have one instance (e.g., "social_i9j0k1l2")

    ID format: {module_prefix}_{uuid8}
    """
    # ===== Identity =====
    instance_id: str  # Unique identifier, format {module_prefix}_{uuid8}
    module_class: str  # Module class name, e.g., "ChatModule", "JobModule"

    # ===== Responsibilities and Status =====
    description: str = ""  # Responsibility description, e.g., "Backend API development for login feature"
    status: InstanceStatus = InstanceStatus.ACTIVE

    # ===== Ownership =====
    agent_id: str  # Owning Agent ID
    linked_narrative_ids: List[str] = []  # Associated Narrative IDs (supports cross-Narrative sharing)

    # ===== Dependencies (for complex task orchestration) =====
    dependencies: List[str] = []  # List of dependent instance_ids

    # ===== Configuration and State (optional, used by Modules as needed) =====
    config: Dict[str, Any] = {}  # Configuration parameters (optional)
    state: Optional[Dict[str, Any]] = None  # Runtime state (optional)

    # ===== Timestamps =====
    created_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # ===== Runtime Bound Module Object (new) =====
    module: Optional["XYZBaseModule"] = Field(
        default=None,
        exclude=True,  # Not serialized to database (temporarily bound at runtime)
        description="Actual Module object bound at runtime, for executing Hooks and getting configuration"
    )

    class Config:
        use_enum_values = True  # Use enum values during serialization
        arbitrary_types_allowed = True  # Allow arbitrary types (Module objects)


class TriggerType(Enum):
    """
    Trigger type enum

    Used to identify how AgentRuntime is triggered
    """
    CHAT = "chat"          # Triggered by user input (synchronous)
    CALLBACK = "callback"  # Triggered by Job completion callback (asynchronous)


class Trigger(BaseModel):
    """
    Trigger - Signal to trigger AgentRuntime

    Two types:
    1. CHAT: Triggered by user input (synchronous execution, blocks user interaction)
    2. CALLBACK: Triggered by Job completion (background execution, does not block user)
    """
    # Basic information
    trigger_type: TriggerType
    timestamp: datetime = Field(default_factory=lambda: datetime.now())

    # CHAT trigger fields
    user_input: Optional[str] = None
    user_id: Optional[str] = None

    # CALLBACK trigger fields
    source_instance_id: Optional[str] = None  # Which instance completed
    callback_data: Optional[Dict[str, Any]] = None  # Completion result data

    class Config:
        use_enum_values = True


class HookCallbackResult(BaseModel):
    """
    Callback result after Hook execution

    Returned by hook_after_event_execution, used to trigger subsequent instances
    """
    # Completed instance_id
    instance_id: str

    # Whether to trigger callback
    trigger_callback: bool = False

    # Instance's final status
    instance_status: InstanceStatus  # COMPLETED or FAILED

    # Optional output data (for use by subsequent instances)
    output_data: Optional[Dict[str, Any]] = None

    # Optional notification message (for the user)
    notification_message: Optional[str] = None


# Rebuild model to resolve forward reference issues
# This is necessary when using TYPE_CHECKING imports
def rebuild_module_instance_model():
    """
    Rebuild ModuleInstance model to resolve forward references

    Call this function after all modules have been imported
    """
    try:
        from xyz_agent_context.module import XYZBaseModule
        ModuleInstance.model_rebuild()
    except ImportError:
        # XYZBaseModule not yet defined, will be rebuilt later
        pass
