"""
@file_name: __init__.py
@author: NetMind.AI
@date: 2026-02-05
@description: MemoryModule package initialization

MemoryModule is the sole external interface for memory management, responsible for:
1. Service methods: search_evermemos(), write_to_evermemos()
2. Hook methods: hook_data_gathering, hook_after_event_execution

External components (e.g., NarrativeService) should obtain instances via get_memory_module().
"""

from .memory_module import MemoryModule, get_memory_module

__all__ = ["MemoryModule", "get_memory_module"]
