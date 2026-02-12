"""
@file_name: agent_inbox.py
@author: NetMind.AI
@date: 2025-12-10
@description: REST API routes for agent inbox messages (agent_messages table)

Provides endpoints for:
- GET /api/agent-inbox - List agent inbox messages
- PUT /api/agent-inbox/{message_id}/respond - Mark message as responded
"""

from typing import Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel
from loguru import logger

from xyz_agent_context.utils.db_factory import get_db_client
from xyz_agent_context.utils import format_for_api
from xyz_agent_context.repository import AgentMessageRepository
from xyz_agent_context.schema.agent_message_schema import MessageSourceType


router = APIRouter()


# =============================================================================
# Response Models
# =============================================================================

class AgentInboxMessageResponse(BaseModel):
    """Agent inbox message response model"""
    message_id: str
    agent_id: str
    source_type: str
    source_id: str
    content: str
    if_response: bool
    narrative_id: Optional[str] = None
    event_id: Optional[str] = None
    created_at: Optional[str] = None


class AgentInboxListResponse(BaseModel):
    """Agent inbox list response model"""
    success: bool
    messages: list[AgentInboxMessageResponse] = []
    count: int = 0
    unresponded_count: int = 0
    error: Optional[str] = None


class MarkRespondedResponse(BaseModel):
    """Mark as responded response model"""
    success: bool
    marked_count: int = 0
    error: Optional[str] = None


# =============================================================================
# Helper Functions
# =============================================================================

def agent_message_to_response(msg) -> AgentInboxMessageResponse:
    """Convert AgentMessage model to response"""
    return AgentInboxMessageResponse(
        message_id=msg.message_id,
        agent_id=msg.agent_id,
        source_type=msg.source_type.value if hasattr(msg.source_type, 'value') else str(msg.source_type),
        source_id=msg.source_id,
        content=msg.content,
        if_response=msg.if_response,
        narrative_id=msg.narrative_id,
        event_id=msg.event_id,
        created_at=format_for_api(msg.created_at),
    )


# =============================================================================
# API Endpoints
# =============================================================================

@router.get("", response_model=AgentInboxListResponse)
async def list_agent_inbox_messages(
    agent_id: str = Query(..., description="Agent ID"),
    source_type: Optional[str] = Query(None, description="Filter by source type (user/agent/system)"),
    if_response: Optional[bool] = Query(None, description="Filter by response status"),
    limit: int = Query(50, description="Max number of messages to return"),
):
    """
    List agent inbox messages for an agent
    """
    logger.info(f"Listing agent inbox for agent: {agent_id}, source_type: {source_type}, if_response: {if_response}")

    try:
        db_client = await get_db_client()
        repo = AgentMessageRepository(db_client)

        # Convert source_type string to enum
        source_type_enum = None
        if source_type:
            try:
                source_type_enum = MessageSourceType(source_type)
            except ValueError:
                pass

        # Get messages
        messages = await repo.get_messages(
            agent_id=agent_id,
            source_type=source_type_enum,
            if_response=if_response,
            limit=limit,
            order_by="created_at DESC"
        )

        # Get unresponded count
        unresponded_messages = await repo.get_unresponded_messages(agent_id, limit=1000)
        unresponded_count = len(unresponded_messages)

        # Convert to response format
        message_responses = [agent_message_to_response(msg) for msg in messages]

        logger.info(f"Found {len(message_responses)} messages, {unresponded_count} unresponded")

        return AgentInboxListResponse(
            success=True,
            messages=message_responses,
            count=len(message_responses),
            unresponded_count=unresponded_count,
        )

    except Exception as e:
        logger.error(f"Error listing agent inbox: {e}")
        return AgentInboxListResponse(
            success=False,
            error=str(e)
        )


@router.put("/{message_id}/respond", response_model=MarkRespondedResponse)
async def mark_message_responded(
    message_id: str,
    narrative_id: Optional[str] = Query(None, description="Associated narrative ID"),
    event_id: Optional[str] = Query(None, description="Associated event ID"),
):
    """
    Mark a message as responded
    """
    logger.info(f"Marking message as responded: {message_id}")

    try:
        db_client = await get_db_client()
        repo = AgentMessageRepository(db_client)

        count = await repo.update_response_status(
            message_id=message_id,
            narrative_id=narrative_id,
            event_id=event_id,
        )

        return MarkRespondedResponse(
            success=True,
            marked_count=count,
        )

    except Exception as e:
        logger.error(f"Error marking message responded: {e}")
        return MarkRespondedResponse(
            success=False,
            error=str(e)
        )
