"""
RAG Store Schema - Gemini RAG Store data model definition

@file_name: rag_store_schema.py
@author: NetMind.AI
@date: 2025-12-02
@description: Defines data models for RAG Store, used to manage Gemini File Search Store metadata

RAG Store is used for:
1. Storing the mapping between agent-user pairs and Gemini File Search Stores
2. Recording the list of uploaded files
3. Maintaining keyword summaries to help the Agent determine whether retrieval is needed

Data table structure:
- display_name: agent_{agent_id}_user_{user_id}, unique identifier
- store_name: Store resource name returned by Gemini API
- keywords: Keyword summary of knowledge base content (max 20)
- uploaded_files: List of uploaded filenames
- agent_id, user_id: Ownership information
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from typing import Union
from pydantic import BaseModel, Field



class RAGStoreModel(BaseModel):
    """
    RAG Store data model

    Stores metadata for Gemini File Search Store, including:
    - Basic info: display_name, store_name
    - Ownership info: agent_id, user_id
    - Content summary: keywords (keyword list, max 20)
    - File records: uploaded_files (list of uploaded filenames)

    Use cases:
    1. Manage agent-user to Gemini Store mapping
    2. Retrieve keywords during hook_data_gathering so the Agent knows the knowledge base content
    3. Record upload history for user viewing
    """

    # === Database ID ===
    id: Optional[int] = Field(
        default=None,
        description="Database auto-increment ID"
    )

    # === Store Identifier ===
    display_name: str = Field(
        ...,
        max_length=255,
        description="Store display name, format: agent_{agent_id}_user_{user_id}"
    )

    store_name: str = Field(
        ...,
        max_length=512,
        description="Store resource name returned by Gemini API, e.g., fileSearchStores/xxx"
    )

    # === Ownership Information ===
    agent_id: str = Field(
        ...,
        max_length=64,
        description="Owning Agent ID"
    )

    user_id: str = Field(
        ...,
        max_length=64,
        description="Owning User ID"
    )

    # === Instance Association (added 2025-12-24) ===
    instance_id: Optional[str] = Field(
        default=None,
        max_length=64,
        description="Associated GeminiRAGModule Instance ID"
    )

    # === Content Summary ===
    keywords: List[Union[str, dict]] = Field(
        default_factory=list,
        description="Keyword summary of knowledge base content, max 20, helps Agent determine if retrieval is needed"
    )

    # === File Records ===
    uploaded_files: List[str] = Field(
        default_factory=list,
        description="List of uploaded filenames (without paths)"
    )

    # === Statistics ===
    file_count: int = Field(
        default=0,
        description="Number of uploaded files"
    )

    # === Timestamps ===
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Creation time"
    )

    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="Update time"
    )


class KeywordsUpdateRequest(BaseModel):
    """
    Keywords update request (LLM output format)

    When uploading new files, calls LLM to analyze existing keywords and new file content,
    generating an updated keyword list.
    """

    keywords: List[str] = Field(
        ...,
        min_items=5,
        max_items=20,
        description="Keyword list, min 5, max 20, should be as abstract and merged as possible, sorted by importance"
    )

    reasoning: Optional[str] = Field(
        description="Reasoning for keyword selection and ordering"
    )
