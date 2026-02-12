"""
@file_name: __init__.py
@author: NetMind.AI
@date: 2025-11-28
@description: FastAPI backend for Agent Context

This package provides:
- WebSocket endpoint for real-time agent runtime streaming
- REST APIs for jobs, inbox, agents, and awareness
"""

from backend.main import app

__all__ = ["app"]
