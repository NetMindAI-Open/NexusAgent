"""
Gemini RAG Module - File Search with Gemini API

This module provides RAG (Retrieval-Augmented Generation) capabilities using
Google's Gemini File Search API.

Components:
- GeminiRAGModule: Main module class with MCP tools
- GeminiRAGTrigger: Static utility methods for document operations
- RAGFileService: Service layer for file management (used by API)

Usage:
    from xyz_agent_context.module.gemini_rag_module import (
        GeminiRAGModule,
        GeminiRAGTrigger,
        RAGFileService,
    )

    # Use trigger for direct uploads
    GeminiRAGTrigger.upload_file(agent_id, user_id, file_path)
    GeminiRAGTrigger.upload_text(agent_id, user_id, content)
    chunks = GeminiRAGTrigger.query(agent_id, user_id, query)

    # Use service for file management
    files = RAGFileService.list_files(agent_id, user_id)
    stats = RAGFileService.get_stats(agent_id, user_id)
"""

from xyz_agent_context.module.gemini_rag_module.gemini_rag_module import GeminiRAGModule
from xyz_agent_context.module.gemini_rag_module.gemini_rag_trigger import GeminiRAGTrigger
from xyz_agent_context.module.gemini_rag_module.rag_file_service import RAGFileService

__all__ = [
    "GeminiRAGModule",
    "GeminiRAGTrigger",
    "RAGFileService",
]
