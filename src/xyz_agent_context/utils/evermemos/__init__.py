"""
EverMemOS Client Utilities

Provides an EverMemOS HTTP API client for:
1. Writing: Event -> HTTP POST /api/v1/memories
2. Retrieval: Query -> HTTP GET /api/v1/memories/search -> aggregate by narrative_id

Usage:
>>> from xyz_agent_context.utils.evermemos import get_evermemos_client
>>> client = get_evermemos_client(agent_id, user_id)
>>> results = await client.search_narratives(query)
"""

from .client import EverMemOSClient, get_evermemos_client

__all__ = ["EverMemOSClient", "get_evermemos_client"]
