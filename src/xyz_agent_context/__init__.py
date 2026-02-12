"""
XYZ Agent Context - Agent context management system

Provides complete context management for Agent runtime:
- Narrative: Narrative management
- Event: Event management  
- Module: Modular capabilities
- Context: Context building
- Runtime: Runtime coordination
"""

__version__ = "0.1.0"

# Export core components - organized by dependency order
# 1. Schema (data structures, no dependencies)
from .schema import (
    ProgressMessage,
    ProgressStatus,
    AgentTextDelta,
    ModuleConfig,
    MCPServerConfig,
    ContextData,
)

# 2. Utils (utilities, low dependencies)
from .utils import DatabaseClient

# 3. Narrative (narrative and event management)
from .narrative import (
    Narrative,
    Event,
    EventService,
    NarrativeService,
)

# 4. Module (module system)
from .module import (
    XYZBaseModule,
    ModuleService,
    HookManager,
)

# 5. Agent Framework (Agent SDK integration)
from .agent_framework import ClaudeAgentSDK

# 6. Context Runtime (context building)
from .context_runtime import ContextRuntime

# 7. Agent Runtime (runtime coordination)
from .agent_runtime import AgentRuntime

__all__ = [
    "__version__",
    "ProgressMessage",
    "ProgressStatus",
    "AgentTextDelta",
    "ModuleConfig",
    "MCPServerConfig",
    "ContextData",
    "DatabaseClient",
    "Narrative",
    "Event",
    "EventService",
    "NarrativeService",
    "XYZBaseModule",
    "ModuleService",
    "HookManager",
    "ClaudeAgentSDK",
    "ContextRuntime",
    "AgentRuntime",
]
