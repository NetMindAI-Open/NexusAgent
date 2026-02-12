"""
@file_name: agents.py
@author: NetMind.AI
@date: 2025-11-28
@description: REST API routes for agents

Provides endpoints for:
- GET /api/agents/{agent_id}/awareness - Get agent awareness
- GET /api/agents/{agent_id}/social-network - Get all social network entities for agent
- GET /api/agents/{agent_id}/social-network/{user_id} - Get user's social network info
- GET /api/agents/{agent_id}/chat-history - Get all narratives and events
- DELETE /api/agents/{agent_id}/history - Clear conversation history
- POST /api/agents/{agent_id}/files - Upload files to agent workspace
- GET /api/agents/{agent_id}/files - List files in agent workspace
- DELETE /api/agents/{agent_id}/files/{filename} - Delete a file from workspace
- GET /api/agents/{agent_id}/mcps - List MCP URLs for agent+user
- POST /api/agents/{agent_id}/mcps - Add new MCP URL
- PUT /api/agents/{agent_id}/mcps/{mcp_id} - Update MCP URL
- DELETE /api/agents/{agent_id}/mcps/{mcp_id} - Delete MCP URL
- POST /api/agents/{agent_id}/mcps/{mcp_id}/validate - Validate MCP connection
- POST /api/agents/{agent_id}/mcps/validate-all - Validate all MCPs

Refactoring notes (2025-12-24):
- Support loading data from new instance_* tables
"""

import os
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query, UploadFile, File
from loguru import logger

from xyz_agent_context.utils.db_factory import get_db_client
from xyz_agent_context.utils import format_for_api
from xyz_agent_context.repository import SocialNetworkRepository, InstanceRepository
from xyz_agent_context.schema import (
    # Awareness
    AwarenessResponse,
    AwarenessUpdateRequest,
    # Social Network
    SocialNetworkEntityInfo,
    SocialNetworkResponse,
    SocialNetworkListResponse,
    SocialNetworkSearchResponse,
    # Chat History
    EventInfo,
    NarrativeInfo,
    ChatHistoryResponse,
    ClearHistoryResponse,
    # Simple Chat History
    SimpleChatMessage,
    SimpleChatHistoryResponse,
    # Files
    FileInfo,
    FileListResponse,
    FileUploadResponse,
    FileDeleteResponse,
    # MCP
    MCPInfo,
    MCPListResponse,
    MCPCreateRequest,
    MCPUpdateRequest,
    MCPResponse,
    MCPValidateResponse,
    MCPValidateAllResponse,
    # RAG Files
    RAGFileInfo,
    RAGFileListResponse,
    RAGFileUploadResponse,
    RAGFileDeleteResponse,
)


router = APIRouter()


@router.get("/{agent_id}/awareness", response_model=AwarenessResponse)
async def get_agent_awareness(agent_id: str):
    """
    Get agent awareness information

    Retrieves data from instance_awareness table (via AwarenessModule's instance_id)
    If no AwarenessModule instance exists, one is automatically created.

    Args:
        agent_id: Agent ID

    Returns:
        AwarenessResponse with awareness content
    """
    import uuid
    from xyz_agent_context.schema.instance_schema import ModuleInstanceRecord, InstanceStatus

    logger.info(f"Getting awareness for agent: {agent_id}")

    try:
        db_client = await get_db_client()

        # 1. Find the AwarenessModule instance for this Agent
        instance_repo = InstanceRepository(db_client)
        instances = await instance_repo.get_by_agent(
            agent_id=agent_id,
            module_class="AwarenessModule"
        )

        if not instances:
            # Automatically create AwarenessModule instance
            logger.info(f"  → No AwarenessModule instance found, creating one for agent: {agent_id}")
            instance_id = f"aware_{uuid.uuid4().hex[:8]}"
            new_instance = ModuleInstanceRecord(
                instance_id=instance_id,
                module_class="AwarenessModule",
                agent_id=agent_id,
                is_public=True,
                status=InstanceStatus.ACTIVE,
                description="Agent self-awareness module instance"
            )
            await instance_repo.create_instance(new_instance)
            logger.info(f"  → Created new instance: {instance_id}")
        else:
            instance_id = instances[0].instance_id

        # 2. Get data from instance_awareness table
        awareness_data = await db_client.get_one(
            "instance_awareness",
            filters={"instance_id": instance_id}
        )

        if awareness_data:
            return AwarenessResponse(
                success=True,
                awareness=awareness_data.get("awareness"),
                create_time=format_for_api(awareness_data.get("created_at")),
                update_time=format_for_api(awareness_data.get("updated_at")),
            )
        else:
            return AwarenessResponse(
                success=False,
                error=f"Awareness data not found for agent: {agent_id}"
            )

    except Exception as e:
        logger.error(f"Error getting awareness: {e}")
        return AwarenessResponse(
            success=False,
            error=str(e)
        )


@router.put("/{agent_id}/awareness", response_model=AwarenessResponse)
async def update_agent_awareness(agent_id: str, request: AwarenessUpdateRequest):
    """
    Update agent awareness information

    Updates data in instance_awareness table (via AwarenessModule's instance_id)
    If no AwarenessModule instance exists, one is automatically created.

    Args:
        agent_id: Agent ID
        request: AwarenessUpdateRequest with new awareness content

    Returns:
        AwarenessResponse with updated awareness content
    """
    import uuid
    from xyz_agent_context.repository import InstanceAwarenessRepository
    from xyz_agent_context.schema.instance_schema import ModuleInstanceRecord, InstanceStatus

    logger.info(f"Updating awareness for agent: {agent_id}")
    logger.info(f"  → Request awareness content (first 100 chars): {request.awareness[:100] if request.awareness else 'None'}...")

    try:
        db_client = await get_db_client()

        # 1. Find the AwarenessModule instance for this Agent
        instance_repo = InstanceRepository(db_client)
        instances = await instance_repo.get_by_agent(
            agent_id=agent_id,
            module_class="AwarenessModule"
        )

        if not instances:
            # Automatically create AwarenessModule instance
            logger.info(f"  → No AwarenessModule instance found, creating one for agent: {agent_id}")
            instance_id = f"aware_{uuid.uuid4().hex[:8]}"
            new_instance = ModuleInstanceRecord(
                instance_id=instance_id,
                module_class="AwarenessModule",
                agent_id=agent_id,
                is_public=True,
                status=InstanceStatus.ACTIVE,
                description="Agent self-awareness module instance"
            )
            await instance_repo.create_instance(new_instance)
            logger.info(f"  → Created new instance: {instance_id}")
        else:
            instance_id = instances[0].instance_id
            logger.info(f"  → Found existing instance_id: {instance_id}")

        # 2. Update instance_awareness table
        awareness_repo = InstanceAwarenessRepository(db_client)
        success = await awareness_repo.upsert(instance_id, request.awareness)
        logger.info(f"  → Upsert result: {success}")

        if success:
            # 3. Return updated data
            awareness_data = await db_client.get_one(
                "instance_awareness",
                filters={"instance_id": instance_id}
            )
            logger.info(f"  → Fetched awareness_data: {awareness_data is not None}")
            if awareness_data:
                logger.info(f"  → Fetched awareness (first 100 chars): {str(awareness_data.get('awareness', ''))[:100]}...")

            return AwarenessResponse(
                success=True,
                awareness=awareness_data.get("awareness") if awareness_data else request.awareness,
                create_time=format_for_api(awareness_data.get("created_at")) if awareness_data else None,
                update_time=format_for_api(awareness_data.get("updated_at")) if awareness_data else None,
            )
        else:
            logger.error(f"  → Upsert failed for instance_id: {instance_id}")
            return AwarenessResponse(
                success=False,
                error="Failed to update awareness"
            )

    except Exception as e:
        logger.error(f"Error updating awareness: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return AwarenessResponse(
            success=False,
            error=str(e)
        )


@router.get("/{agent_id}/social-network/{user_id}", response_model=SocialNetworkResponse)
async def get_user_social_network_info(agent_id: str, user_id: str):
    """
    Get user's social network information from the agent's perspective

    Retrieves data from instance_social_entities table (via SocialNetworkModule's instance_id)

    Args:
        agent_id: Agent ID (owner of the social network)
        user_id: User ID to look up

    Returns:
        SocialNetworkResponse with entity information
    """
    logger.info(f"Getting social network info for user: {user_id}, agent: {agent_id}")

    try:
        db_client = await get_db_client()

        # 1. Find the SocialNetworkModule instance for this Agent
        instance_repo = InstanceRepository(db_client)
        instances = await instance_repo.get_by_agent(
            agent_id=agent_id,
            module_class="SocialNetworkModule"
        )

        if not instances:
            return SocialNetworkResponse(
                success=False,
                error=f"No SocialNetworkModule instance found for agent: {agent_id}"
            )

        instance_id = instances[0].instance_id

        # 2. Get data from instance_social_entities table
        entity_data = await db_client.get_one(
            "instance_social_entities",
            filters={"instance_id": instance_id, "entity_id": user_id}
        )

        if entity_data:
            entity_info = SocialNetworkEntityInfo(
                entity_id=entity_data.get("entity_id"),
                entity_name=entity_data.get("entity_name"),
                entity_description=entity_data.get("entity_description"),
                entity_type=entity_data.get("entity_type"),
                identity_info=_parse_json(entity_data.get("identity_info"), {}),
                contact_info=_parse_json(entity_data.get("contact_info"), {}),
                tags=_parse_json(entity_data.get("tags"), []),
                relationship_strength=entity_data.get("relationship_strength", 0.0),
                interaction_count=entity_data.get("interaction_count", 0),
                last_interaction_time=format_for_api(entity_data.get("last_interaction_time")),
            )
            return SocialNetworkResponse(
                success=True,
                entity=entity_info
            )
        else:
            return SocialNetworkResponse(
                success=False,
                error=f"No social network info found for user: {user_id}"
            )

    except Exception as e:
        logger.error(f"Error getting social network info: {e}")
        return SocialNetworkResponse(
            success=False,
            error=str(e)
        )


def _parse_json(value: Any, default: Any) -> Any:
    """
    Parse JSON field

    Handles JSON strings stored in the database, converting them to Python objects.
    Supports dict and list type JSON.
    Also handles double-encoding cases (JSON strings that were JSON-encoded again).
    """
    import json
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        # Already a Python object, return directly
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            # Handle double-encoding: if parsed result is still a string, try parsing again
            if isinstance(parsed, str):
                try:
                    parsed = json.loads(parsed)
                except json.JSONDecodeError:
                    pass  # Not double-encoded, return first parse result
            return parsed
        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse failed for value: {value[:100]}... Error: {e}")
            return default
    # Other types, return default value
    logger.warning(f"Unexpected type for JSON field: {type(value)}, value: {value}")
    return default


@router.get("/{agent_id}/social-network", response_model=SocialNetworkListResponse)
async def get_all_social_network_entities(agent_id: str):
    """
    Get all social network entities for an agent

    Retrieves data from instance_social_entities table (via SocialNetworkModule's instance_id)

    Args:
        agent_id: Agent ID (owner of the social network)

    Returns:
        SocialNetworkListResponse with all entities
    """
    logger.info(f"Getting all social network entities for agent: {agent_id}")

    try:
        db_client = await get_db_client()

        # 1. Find the SocialNetworkModule instance for this Agent
        instance_repo = InstanceRepository(db_client)
        instances = await instance_repo.get_by_agent(
            agent_id=agent_id,
            module_class="SocialNetworkModule"
        )

        if not instances:
            return SocialNetworkListResponse(
                success=True,
                entities=[],
                count=0
            )

        instance_id = instances[0].instance_id

        # 2. Get all entities from instance_social_entities table
        entities_data = await db_client.get(
            "instance_social_entities",
            filters={"instance_id": instance_id},
            order_by="updated_at DESC",
            limit=1000
        )

        entity_list = []
        for entity_data in entities_data:
            entity_info = SocialNetworkEntityInfo(
                entity_id=entity_data.get("entity_id"),
                entity_name=entity_data.get("entity_name"),
                entity_description=entity_data.get("entity_description"),
                entity_type=entity_data.get("entity_type"),
                identity_info=_parse_json(entity_data.get("identity_info"), {}),
                contact_info=_parse_json(entity_data.get("contact_info"), {}),
                tags=_parse_json(entity_data.get("tags"), []),
                relationship_strength=entity_data.get("relationship_strength", 0.0),
                interaction_count=entity_data.get("interaction_count", 0),
                last_interaction_time=format_for_api(entity_data.get("last_interaction_time")),
                # New fields (Feature 2.2, 2.3)
                persona=entity_data.get("persona"),
                related_job_ids=_parse_json(entity_data.get("related_job_ids"), []),
                expertise_domains=_parse_json(entity_data.get("expertise_domains"), []),
            )
            entity_list.append(entity_info)

        return SocialNetworkListResponse(
            success=True,
            entities=entity_list,
            count=len(entity_list)
        )

    except Exception as e:
        logger.error(f"Error getting social network entities: {e}")
        return SocialNetworkListResponse(
            success=False,
            error=str(e)
        )


@router.get("/{agent_id}/social-network/search", response_model=SocialNetworkSearchResponse)
async def search_social_network_entities(
    agent_id: str,
    query: str = Query(..., description="Search query"),
    search_type: str = Query("semantic", description="Search type: 'keyword' or 'semantic'"),
    limit: int = Query(10, description="Maximum number of results")
):
    """
    Search social network entities by keyword or semantic similarity

    Supports two search modes:
    - keyword: Keyword matching (searches in entity_name, entity_description, tags)
    - semantic: Semantic similarity search (based on embedding vectors)

    Args:
        agent_id: Agent ID
        query: Search query string
        search_type: 'keyword' or 'semantic'
        limit: Maximum number of results

    Returns:
        SocialNetworkSearchResponse with matching entities
    """
    logger.info(f"Searching social network entities: agent={agent_id}, query='{query}', type={search_type}")

    try:
        db_client = await get_db_client()

        # 1. Find the SocialNetworkModule instance for this Agent
        instance_repo = InstanceRepository(db_client)
        instances = await instance_repo.get_by_agent(
            agent_id=agent_id,
            module_class="SocialNetworkModule"
        )

        if not instances:
            return SocialNetworkSearchResponse(
                success=True,
                entities=[],
                count=0,
                search_type=search_type
            )

        instance_id = instances[0].instance_id

        # 2. Execute search based on search type
        social_repo = SocialNetworkRepository(db_client)

        if search_type == "semantic":
            # Semantic search
            from xyz_agent_context.utils.embedding import get_embedding
            query_embedding = await get_embedding(query)
            results = await social_repo.semantic_search(
                instance_id=instance_id,
                query_embedding=query_embedding,
                limit=limit
            )
            # results is List[Tuple[Entity, float]]
            entity_list = []
            for entity, score in results:
                entity_info = SocialNetworkEntityInfo(
                    entity_id=entity.entity_id,
                    entity_name=entity.entity_name,
                    entity_description=entity.entity_description,
                    entity_type=entity.entity_type,
                    identity_info=entity.identity_info or {},
                    contact_info=entity.contact_info or {},
                    tags=entity.tags or [],
                    relationship_strength=entity.relationship_strength or 0.0,
                    interaction_count=entity.interaction_count or 0,
                    last_interaction_time=format_for_api(entity.last_interaction_time),
                    persona=entity.persona,
                    related_job_ids=entity.related_job_ids or [],
                    expertise_domains=entity.expertise_domains or [],
                    similarity_score=round(score, 4)
                )
                entity_list.append(entity_info)
        else:
            # Keyword search
            results = await social_repo.keyword_search(
                instance_id=instance_id,
                keyword=query,
                limit=limit
            )
            entity_list = []
            for entity in results:
                entity_info = SocialNetworkEntityInfo(
                    entity_id=entity.entity_id,
                    entity_name=entity.entity_name,
                    entity_description=entity.entity_description,
                    entity_type=entity.entity_type,
                    identity_info=entity.identity_info or {},
                    contact_info=entity.contact_info or {},
                    tags=entity.tags or [],
                    relationship_strength=entity.relationship_strength or 0.0,
                    interaction_count=entity.interaction_count or 0,
                    last_interaction_time=format_for_api(entity.last_interaction_time),
                    persona=entity.persona,
                    related_job_ids=entity.related_job_ids or [],
                    expertise_domains=entity.expertise_domains or [],
                )
                entity_list.append(entity_info)

        return SocialNetworkSearchResponse(
            success=True,
            entities=entity_list,
            count=len(entity_list),
            search_type=search_type
        )

    except Exception as e:
        logger.error(f"Error searching social network entities: {e}")
        return SocialNetworkSearchResponse(
            success=False,
            error=str(e),
            search_type=search_type
        )


@router.get("/{agent_id}/chat-history", response_model=ChatHistoryResponse)
async def get_chat_history(
    agent_id: str,
    user_id: Optional[str] = Query(None, description="Optional user ID to filter")
):
    """
    Get all narratives and events for chat history

    Improved query logic: not only relies on narrative_info.actors, but also supplements queries
    based on ChatModule instances. This way, even if Narrative actors are not correctly set,
    the user's chat history can still be returned.

    Args:
        agent_id: Agent ID
        user_id: Optional user ID to filter narratives

    Returns:
        ChatHistoryResponse with narratives and events
    """
    import json

    logger.info(f"Getting chat history for agent: {agent_id}, user: {user_id}")

    try:
        db_client = await get_db_client()
        instance_repo = InstanceRepository(db_client)

        narrative_ids = []
        narrative_map = {}  # narrative_id -> narrative_info

        # ===== Method 1: Find associated Narratives based on ChatModule instances =====
        # This is the preferred method because the instance's user_id is reliable
        if user_id:
            all_instances = await instance_repo.get_by_agent_and_user(
                agent_id=agent_id,
                user_id=user_id,
                include_public=False
            )
            chat_instances = [inst for inst in all_instances if inst.module_class == "ChatModule"]

            logger.info(f"Found {len(chat_instances)} ChatModule instances for user={user_id}")

            # Get the narrative_ids associated with these instances
            for inst in chat_instances:
                links = await db_client.get(
                    "instance_narrative_links",
                    filters={"instance_id": inst.instance_id}
                )
                for link in links:
                    nar_id = link.get("narrative_id")
                    if nar_id and nar_id not in narrative_ids:
                        narrative_ids.append(nar_id)

            # Load details of these narratives
            # Note: orphan links may exist (narrative deleted but link still present)
            valid_narrative_ids = []
            for nar_id in narrative_ids:
                nar_row = await db_client.get_one("narratives", {"narrative_id": nar_id})
                if nar_row:
                    valid_narrative_ids.append(nar_id)
                    narrative_info_raw = nar_row.get("narrative_info")
                    narrative_info = {}
                    if narrative_info_raw:
                        try:
                            narrative_info = json.loads(narrative_info_raw) if isinstance(narrative_info_raw, str) else narrative_info_raw
                        except (json.JSONDecodeError, TypeError):
                            pass

                    # Ensure actors includes the current user
                    actors = narrative_info.get("actors", [])
                    if not any(a.get("id") == user_id for a in actors):
                        actors.append({"id": user_id, "type": "user"})

                    narrative_map[nar_id] = {
                        "narrative_id": nar_id,
                        "name": narrative_info.get("name", f"Conversation with {user_id}"),
                        "description": narrative_info.get("description", ""),
                        "current_summary": narrative_info.get("current_summary", ""),
                        "actors": actors,
                        "created_at": format_for_api(nar_row.get("created_at")),
                        "updated_at": format_for_api(nar_row.get("updated_at")),
                    }

            # Use validated narrative_ids
            narrative_ids = valid_narrative_ids

        # ===== Method 2: Fallback to query based on narrative_info.actors (compatible with old data) =====
        if not narrative_ids:
            narratives_raw = await db_client.get(
                "narratives",
                filters={"agent_id": agent_id},
                order_by="created_at ASC"
            )

            if not narratives_raw:
                return ChatHistoryResponse(success=True)

            for narrative in narratives_raw:
                narrative_id = narrative.get("narrative_id")
                if not narrative_id:
                    continue

                narrative_info_raw = narrative.get("narrative_info")
                if narrative_info_raw:
                    try:
                        if isinstance(narrative_info_raw, str):
                            narrative_info = json.loads(narrative_info_raw)
                        else:
                            narrative_info = narrative_info_raw

                        if user_id:
                            actors = narrative_info.get("actors", [])
                            user_in_actors = any(
                                actor.get("id") == user_id
                                for actor in actors
                            )
                            if not user_in_actors:
                                continue

                        narrative_ids.append(narrative_id)
                        narrative_map[narrative_id] = {
                            "narrative_id": narrative_id,
                            "name": narrative_info.get("name", ""),
                            "description": narrative_info.get("description", ""),
                            "current_summary": narrative_info.get("current_summary", ""),
                            "actors": narrative_info.get("actors", []),
                            "created_at": format_for_api(narrative.get("created_at")),
                            "updated_at": format_for_api(narrative.get("updated_at")),
                        }
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(f"Failed to parse narrative_info: {narrative_id}, error: {e}")
                        continue

        if not narrative_ids:
            return ChatHistoryResponse(success=True)

        # 2.5 Query instances for each narrative
        from xyz_agent_context.schema.api_schema import InstanceInfo

        for narrative_id in narrative_ids:
            # Query instance_narrative_links to get associated instance_ids
            links = await db_client.get(
                "instance_narrative_links",
                filters={"narrative_id": narrative_id, "link_type": "active"}
            )
            instance_ids = [link.get("instance_id") for link in links if link.get("instance_id")]

            # Query module_instances for details
            instances = []
            for instance_id in instance_ids:
                instance_rows = await db_client.get(
                    "module_instances",
                    filters={"instance_id": instance_id}
                )
                if instance_rows:
                    inst = instance_rows[0]
                    # Skip cancelled and archived Instances (not displayed in frontend)
                    status = inst.get("status", "active")
                    if status in ("cancelled", "archived"):
                        continue

                    # Parse JSON fields
                    config_raw = inst.get("config")
                    config = {}
                    if config_raw:
                        try:
                            config = json.loads(config_raw) if isinstance(config_raw, str) else config_raw
                        except (json.JSONDecodeError, TypeError):
                            pass

                    deps_raw = inst.get("dependencies")
                    deps = []
                    if deps_raw:
                        try:
                            deps = json.loads(deps_raw) if isinstance(deps_raw, str) else deps_raw
                        except (json.JSONDecodeError, TypeError):
                            pass

                    instances.append(InstanceInfo(
                        instance_id=inst.get("instance_id", ""),
                        module_class=inst.get("module_class", ""),
                        description=inst.get("description", ""),
                        status=status,
                        dependencies=deps,
                        config=config,
                        created_at=format_for_api(inst.get("created_at")),
                        user_id=inst.get("user_id")  # Used by frontend to filter events by user_id
                    ))

            # Add to narrative_map
            if narrative_id in narrative_map:
                narrative_map[narrative_id]["instances"] = instances

        # 3. Query all events for these narratives
        events_raw = []
        for narrative_id in narrative_ids:
            narrative_events = await db_client.get(
                "events",
                filters={"narrative_id": narrative_id},
                order_by="created_at ASC"
            )
            events_raw.extend(narrative_events)

        # Sort all events by created_at
        events_raw.sort(key=lambda e: e.get("created_at", ""))

        # 4. Build response
        narratives = [
            NarrativeInfo(**narrative_map[nid])
            for nid in narrative_ids
        ]

        events = []
        for event in events_raw:
            event_id = event.get("event_id") or event.get("id")
            narrative_id = event.get("narrative_id")

            # Parse event_log
            event_log_raw = event.get("event_log")
            event_log = []
            if event_log_raw:
                try:
                    if isinstance(event_log_raw, str):
                        event_log = json.loads(event_log_raw)
                    else:
                        event_log = event_log_raw
                except (json.JSONDecodeError, TypeError):
                    pass

            events.append(EventInfo(
                event_id=event_id,
                narrative_id=narrative_id,
                narrative_name=narrative_map.get(narrative_id, {}).get("name"),
                trigger=event.get("trigger", ""),
                trigger_source=event.get("trigger_source", ""),
                user_id=event.get("user_id"),
                final_output=event.get("final_output", ""),
                created_at=format_for_api(event.get("created_at")),
                event_log=event_log,
            ))

        return ChatHistoryResponse(
            success=True,
            narratives=narratives,
            events=events,
            narrative_count=len(narratives),
            event_count=len(events),
        )

    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        return ChatHistoryResponse(
            success=False,
            error=str(e)
        )


@router.delete("/{agent_id}/history", response_model=ClearHistoryResponse)
async def clear_conversation_history(
    agent_id: str,
    user_id: Optional[str] = Query(None, description="Optional user ID to filter")
):
    """
    Clear conversation history for an agent

    Search logic:
    1. Query all narratives for the given agent_id
    2. Parse narrative_info JSON field, check if actors list contains user_id
    3. Delete matching narratives and all their associated events

    Args:
        agent_id: Agent ID
        user_id: Optional user ID to filter (if not provided, clears all)

    Returns:
        ClearHistoryResponse with deletion statistics
    """
    import json

    logger.info(f"Clearing history for agent: {agent_id}, user: {user_id}")

    try:
        db_client = await get_db_client()

        # 1. Query all narratives for this agent
        narrative_filters = {"agent_id": agent_id}
        narratives = await db_client.get("narratives", filters=narrative_filters)

        if not narratives:
            logger.info("No narratives found to delete")
            return ClearHistoryResponse(success=True)

        logger.info(f"Found {len(narratives)} narratives")

        # 2. Filter by user_id if specified
        # user_id is stored in narrative_info.actors
        narrative_ids_to_delete = []

        if user_id:
            for narrative in narratives:
                narrative_id = narrative.get("narrative_id")
                if not narrative_id:
                    continue

                # Parse narrative_info JSON field
                narrative_info_raw = narrative.get("narrative_info")
                if narrative_info_raw:
                    try:
                        # If it's a string, parse JSON
                        if isinstance(narrative_info_raw, str):
                            narrative_info = json.loads(narrative_info_raw)
                        else:
                            narrative_info = narrative_info_raw

                        # Check if user_id is in actors list
                        actors = narrative_info.get("actors", [])
                        user_in_actors = any(
                            actor.get("id") == user_id
                            for actor in actors
                        )

                        if user_in_actors:
                            narrative_ids_to_delete.append(narrative_id)
                            logger.debug(f"Narrative {narrative_id} contains user {user_id}")
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.warning(f"Failed to parse narrative_info: {narrative_id}, error: {e}")
                        continue
        else:
            # If no user_id specified, delete all narratives
            narrative_ids_to_delete = [
                n.get("narrative_id") for n in narratives
                if n.get("narrative_id")
            ]

        if not narrative_ids_to_delete:
            logger.info(f"No matching records to delete (agent_id={agent_id}, user_id={user_id})")
            return ClearHistoryResponse(success=True)

        logger.info(f"Will delete {len(narrative_ids_to_delete)} narratives: {narrative_ids_to_delete}")

        # 3. Delete events and narratives in transaction
        events_deleted = 0
        narratives_deleted = 0

        async with db_client.transaction():
            # Delete all events for each narrative
            for narrative_id in narrative_ids_to_delete:
                event_filters = {"narrative_id": narrative_id}
                count = await db_client.delete("events", filters=event_filters)
                events_deleted += count
                logger.debug(f"Deleted {count} events for narrative_id={narrative_id}")

            # Delete narratives
            for narrative_id in narrative_ids_to_delete:
                count = await db_client.delete(
                    "narratives",
                    filters={"narrative_id": narrative_id}
                )
                narratives_deleted += count

        logger.info(f"Deleted {narratives_deleted} narratives and {events_deleted} events")

        return ClearHistoryResponse(
            success=True,
            narrative_ids_deleted=narrative_ids_to_delete,
            narratives_count=narratives_deleted,
            events_count=events_deleted,
        )

    except Exception as e:
        logger.error(f"Error clearing history: {e}")
        return ClearHistoryResponse(
            success=False,
            error=str(e)
        )


# ===== File Management Endpoints =====


def get_workspace_path(agent_id: str, user_id: str) -> str:
    """Get the workspace path for an agent-user pair"""
    from xyz_agent_context.settings import settings
    base_path = settings.base_working_path
    return os.path.join(base_path, f"{agent_id}_{user_id}")


@router.get("/{agent_id}/files", response_model=FileListResponse)
async def list_workspace_files(
    agent_id: str,
    user_id: str = Query(..., description="User ID")
):
    """
    List all files in the agent workspace

    Args:
        agent_id: Agent ID
        user_id: User ID

    Returns:
        FileListResponse with list of files
    """
    logger.info(f"Listing files for agent: {agent_id}, user: {user_id}")

    try:
        workspace_path = get_workspace_path(agent_id, user_id)

        if not os.path.exists(workspace_path):
            return FileListResponse(
                success=True,
                files=[],
                workspace_path=workspace_path,
            )

        files = []
        for filename in os.listdir(workspace_path):
            filepath = os.path.join(workspace_path, filename)
            if os.path.isfile(filepath):
                stat = os.stat(filepath)
                files.append(FileInfo(
                    filename=filename,
                    size=stat.st_size,
                    modified_at=str(stat.st_mtime),
                ))

        # Sort by modified time descending
        files.sort(key=lambda f: f.modified_at, reverse=True)

        return FileListResponse(
            success=True,
            files=files,
            workspace_path=workspace_path,
        )

    except Exception as e:
        logger.error(f"Error listing files: {e}")
        return FileListResponse(
            success=False,
            error=str(e)
        )


@router.post("/{agent_id}/files", response_model=FileUploadResponse)
async def upload_file(
    agent_id: str,
    user_id: str = Query(..., description="User ID"),
    file: UploadFile = File(..., description="File to upload"),
):
    """
    Upload a file to the agent workspace

    Args:
        agent_id: Agent ID
        user_id: User ID
        file: File to upload

    Returns:
        FileUploadResponse with upload result
    """
    logger.info(f"Uploading file '{file.filename}' for agent: {agent_id}, user: {user_id}")

    try:
        # Security check: prevent path traversal attacks
        safe_filename = os.path.basename(file.filename)
        if safe_filename != file.filename or '..' in file.filename:
            return FileUploadResponse(
                success=False,
                error="Invalid filename: path traversal not allowed"
            )

        workspace_path = get_workspace_path(agent_id, user_id)

        # Create workspace directory if it doesn't exist
        if not os.path.exists(workspace_path):
            os.makedirs(workspace_path)
            logger.info(f"Created workspace directory: {workspace_path}")

        # Save the file
        filepath = os.path.join(workspace_path, safe_filename)
        content = await file.read()

        with open(filepath, "wb") as f:
            f.write(content)

        file_size = len(content)
        logger.info(f"File saved: {filepath} ({file_size} bytes)")

        return FileUploadResponse(
            success=True,
            filename=file.filename,
            size=file_size,
            workspace_path=workspace_path,
        )

    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        return FileUploadResponse(
            success=False,
            error=str(e)
        )


@router.delete("/{agent_id}/files/{filename}", response_model=FileDeleteResponse)
async def delete_file(
    agent_id: str,
    filename: str,
    user_id: str = Query(..., description="User ID"),
):
    """
    Delete a file from the agent workspace

    Args:
        agent_id: Agent ID
        filename: Name of the file to delete
        user_id: User ID

    Returns:
        FileDeleteResponse with deletion result
    """
    logger.info(f"Deleting file '{filename}' for agent: {agent_id}, user: {user_id}")

    try:
        # Security check: prevent path traversal attacks
        if os.path.basename(filename) != filename or '..' in filename:
            return FileDeleteResponse(
                success=False,
                error="Invalid filename: path traversal not allowed"
            )

        workspace_path = get_workspace_path(agent_id, user_id)
        filepath = os.path.join(workspace_path, filename)

        # Secondary security check: ensure file path is within workspace
        if not os.path.abspath(filepath).startswith(os.path.abspath(workspace_path)):
            return FileDeleteResponse(
                success=False,
                error="Invalid filename: path traversal not allowed"
            )

        if not os.path.exists(filepath):
            return FileDeleteResponse(
                success=False,
                error=f"File not found: {filename}"
            )

        os.remove(filepath)
        logger.info(f"File deleted: {filepath}")

        return FileDeleteResponse(
            success=True,
            filename=filename,
        )

    except Exception as e:
        logger.error(f"Error deleting file: {e}")
        return FileDeleteResponse(
            success=False,
            error=str(e)
        )


# ===== MCP Management Endpoints =====

from xyz_agent_context.repository import MCPRepository
from xyz_agent_context.repository.mcp_repository import validate_mcp_sse_connection
from xyz_agent_context.schema import MCPUrl


def mcp_to_info(mcp: MCPUrl) -> MCPInfo:
    """Convert MCPUrl model to MCPInfo response"""
    return MCPInfo(
        mcp_id=mcp.mcp_id,
        agent_id=mcp.agent_id,
        user_id=mcp.user_id,
        name=mcp.name,
        url=mcp.url,
        description=mcp.description,
        is_enabled=mcp.is_enabled,
        connection_status=mcp.connection_status,
        last_check_time=format_for_api(mcp.last_check_time),
        last_error=mcp.last_error,
        created_at=format_for_api(mcp.created_at),
        updated_at=format_for_api(mcp.updated_at),
    )


@router.get("/{agent_id}/mcps", response_model=MCPListResponse)
async def list_mcps(
    agent_id: str,
    user_id: str = Query(..., description="User ID"),
):
    """
    List all MCP URLs for an agent+user pair

    Args:
        agent_id: Agent ID
        user_id: User ID

    Returns:
        MCPListResponse with list of MCPs
    """
    logger.info(f"Listing MCPs for agent: {agent_id}, user: {user_id}")

    try:
        db_client = await get_db_client()
        repo = MCPRepository(db_client)
        mcps = await repo.get_mcps_by_agent_user(
            agent_id=agent_id,
            user_id=user_id
        )

        mcp_list = [mcp_to_info(mcp) for mcp in mcps]

        return MCPListResponse(
            success=True,
            mcps=mcp_list,
            count=len(mcp_list),
        )

    except Exception as e:
        logger.error(f"Error listing MCPs: {e}")
        return MCPListResponse(
            success=False,
            error=str(e)
        )


@router.post("/{agent_id}/mcps", response_model=MCPResponse)
async def create_mcp(
    agent_id: str,
    request: MCPCreateRequest,
    user_id: str = Query(..., description="User ID"),
):
    """
    Create a new MCP URL

    Args:
        agent_id: Agent ID
        request: MCP creation request
        user_id: User ID

    Returns:
        MCPResponse with created MCP
    """
    import uuid

    logger.info(f"Creating MCP for agent: {agent_id}, user: {user_id}, name: {request.name}")

    try:
        # Validate that URL looks like an SSE endpoint
        if not request.url.startswith(("http://", "https://")):
            return MCPResponse(
                success=False,
                error="URL must start with http:// or https://"
            )

        db_client = await get_db_client()
        repo = MCPRepository(db_client)

        # Generate a unique mcp_id
        mcp_id = f"mcp_{uuid.uuid4().hex[:8]}"

        # Add the MCP
        record_id = await repo.add_mcp(
            agent_id=agent_id,
            user_id=user_id,
            mcp_id=mcp_id,
            name=request.name,
            url=request.url,
            description=request.description,
            is_enabled=request.is_enabled
        )

        # Get the created MCP to return full info
        mcps = await repo.get_mcps_by_agent_user(agent_id, user_id)
        created_mcp = next((m for m in mcps if m.id == record_id), None)

        if created_mcp:
            return MCPResponse(
                success=True,
                mcp=mcp_to_info(created_mcp),
            )
        else:
            return MCPResponse(
                success=True,
                mcp=None,
            )

    except Exception as e:
        logger.error(f"Error creating MCP: {e}")
        return MCPResponse(
            success=False,
            error=str(e)
        )


@router.put("/{agent_id}/mcps/{mcp_id}", response_model=MCPResponse)
async def update_mcp_endpoint(
    agent_id: str,
    mcp_id: str,
    request: MCPUpdateRequest,
    user_id: str = Query(..., description="User ID"),
):
    """
    Update an existing MCP URL

    Args:
        agent_id: Agent ID
        mcp_id: MCP ID to update
        request: MCP update request
        user_id: User ID

    Returns:
        MCPResponse with updated MCP
    """
    logger.info(f"Updating MCP {mcp_id} for agent: {agent_id}, user: {user_id}")

    try:
        db_client = await get_db_client()
        repo = MCPRepository(db_client)

        # Check MCP exists and belongs to this agent+user
        existing_mcp = await repo.get_mcp(mcp_id)
        if not existing_mcp:
            return MCPResponse(
                success=False,
                error=f"MCP not found: {mcp_id}"
            )

        if existing_mcp.agent_id != agent_id or existing_mcp.user_id != user_id:
            return MCPResponse(
                success=False,
                error="MCP does not belong to this agent+user"
            )

        # Validate URL if provided
        if request.url and not request.url.startswith(("http://", "https://")):
            return MCPResponse(
                success=False,
                error="URL must start with http:// or https://"
            )

        # Update the MCP
        await repo.update_mcp(
            mcp_id=mcp_id,
            name=request.name,
            url=request.url,
            description=request.description,
            is_enabled=request.is_enabled
        )

        # Get updated MCP
        updated_mcp = await repo.get_mcp(mcp_id)

        return MCPResponse(
            success=True,
            mcp=mcp_to_info(updated_mcp) if updated_mcp else None,
        )

    except Exception as e:
        logger.error(f"Error updating MCP: {e}")
        return MCPResponse(
            success=False,
            error=str(e)
        )


@router.delete("/{agent_id}/mcps/{mcp_id}", response_model=MCPResponse)
async def delete_mcp_endpoint(
    agent_id: str,
    mcp_id: str,
    user_id: str = Query(..., description="User ID"),
):
    """
    Delete an MCP URL

    Args:
        agent_id: Agent ID
        mcp_id: MCP ID to delete
        user_id: User ID

    Returns:
        MCPResponse with deletion result
    """
    logger.info(f"Deleting MCP {mcp_id} for agent: {agent_id}, user: {user_id}")

    try:
        db_client = await get_db_client()
        repo = MCPRepository(db_client)

        # Check MCP exists and belongs to this agent+user
        existing_mcp = await repo.get_mcp(mcp_id)
        if not existing_mcp:
            return MCPResponse(
                success=False,
                error=f"MCP not found: {mcp_id}"
            )

        if existing_mcp.agent_id != agent_id or existing_mcp.user_id != user_id:
            return MCPResponse(
                success=False,
                error="MCP does not belong to this agent+user"
            )

        # Delete the MCP
        await repo.delete_mcp(mcp_id)

        return MCPResponse(
            success=True,
            mcp=mcp_to_info(existing_mcp),
        )

    except Exception as e:
        logger.error(f"Error deleting MCP: {e}")
        return MCPResponse(
            success=False,
            error=str(e)
        )


@router.post("/{agent_id}/mcps/{mcp_id}/validate", response_model=MCPValidateResponse)
async def validate_mcp_endpoint(
    agent_id: str,
    mcp_id: str,
    user_id: str = Query(..., description="User ID"),
):
    """
    Validate MCP SSE connection

    Args:
        agent_id: Agent ID
        mcp_id: MCP ID to validate
        user_id: User ID

    Returns:
        MCPValidateResponse with validation result
    """
    logger.info(f"Validating MCP {mcp_id} for agent: {agent_id}, user: {user_id}")

    try:
        db_client = await get_db_client()
        repo = MCPRepository(db_client)

        # Check MCP exists and belongs to this agent+user
        existing_mcp = await repo.get_mcp(mcp_id)
        if not existing_mcp:
            return MCPValidateResponse(
                success=False,
                mcp_id=mcp_id,
                connected=False,
                error=f"MCP not found: {mcp_id}"
            )

        if existing_mcp.agent_id != agent_id or existing_mcp.user_id != user_id:
            return MCPValidateResponse(
                success=False,
                mcp_id=mcp_id,
                connected=False,
                error="MCP does not belong to this agent+user"
            )

        # Validate the connection
        connected, error = await validate_mcp_sse_connection(existing_mcp.url)

        # Update connection status in database
        status = "connected" if connected else "failed"
        await repo.update_connection_status(
            mcp_id=mcp_id,
            status=status,
            error=error
        )

        return MCPValidateResponse(
            success=True,
            mcp_id=mcp_id,
            connected=connected,
            error=error,
        )

    except Exception as e:
        logger.error(f"Error validating MCP: {e}")
        return MCPValidateResponse(
            success=False,
            mcp_id=mcp_id,
            connected=False,
            error=str(e)
        )


@router.post("/{agent_id}/mcps/validate-all", response_model=MCPValidateAllResponse)
async def validate_all_mcps_endpoint(
    agent_id: str,
    user_id: str = Query(..., description="User ID"),
):
    """
    Validate all MCP SSE connections for an agent+user pair

    Runs validation in parallel for better performance

    Args:
        agent_id: Agent ID
        user_id: User ID

    Returns:
        MCPValidateAllResponse with all validation results
    """
    import asyncio

    logger.info(f"Validating all MCPs for agent: {agent_id}, user: {user_id}")

    try:
        db_client = await get_db_client()
        repo = MCPRepository(db_client)

        # Get all MCPs
        mcps = await repo.get_mcps_by_agent_user(
            agent_id=agent_id,
            user_id=user_id
        )

        if not mcps:
            return MCPValidateAllResponse(
                success=True,
                results=[],
                total=0,
                connected=0,
                failed=0,
            )

        # Validate all MCPs in parallel
        async def validate_single(mcp: MCPUrl) -> MCPValidateResponse:
            connected, error = await validate_mcp_sse_connection(mcp.url)

            # Update connection status
            status = "connected" if connected else "failed"
            await repo.update_connection_status(
                mcp_id=mcp.mcp_id,
                status=status,
                error=error
            )

            return MCPValidateResponse(
                success=True,
                mcp_id=mcp.mcp_id,
                connected=connected,
                error=error,
            )

        # Run all validations in parallel
        results = await asyncio.gather(*[validate_single(mcp) for mcp in mcps])

        connected_count = sum(1 for r in results if r.connected)
        failed_count = sum(1 for r in results if not r.connected)

        return MCPValidateAllResponse(
            success=True,
            results=results,
            total=len(results),
            connected=connected_count,
            failed=failed_count,
        )

    except Exception as e:
        logger.error(f"Error validating all MCPs: {e}")
        return MCPValidateAllResponse(
            success=False,
            error=str(e)
        )


# ===== RAG File Management Endpoints =====

from xyz_agent_context.module.gemini_rag_module.rag_file_service import RAGFileService


@router.get("/{agent_id}/rag-files", response_model=RAGFileListResponse)
async def list_rag_files(
    agent_id: str,
    user_id: str = Query(..., description="User ID"),
):
    """
    List all RAG files for an agent-user pair with their upload status

    Args:
        agent_id: Agent ID
        user_id: User ID

    Returns:
        RAGFileListResponse with list of files and their status
    """
    logger.info(f"Listing RAG files for agent: {agent_id}, user: {user_id}")

    try:
        # Call service layer to get file list
        files_data = RAGFileService.list_files(agent_id, user_id)
        stats = RAGFileService.get_stats(agent_id, user_id)

        files = [RAGFileInfo(**f) for f in files_data]

        return RAGFileListResponse(
            success=True,
            files=files,
            total_count=stats["total_count"],
            completed_count=stats["completed_count"],
            pending_count=stats["pending_count"],
        )

    except Exception as e:
        logger.error(f"Error listing RAG files: {e}")
        return RAGFileListResponse(
            success=False,
            error=str(e)
        )


@router.post("/{agent_id}/rag-files", response_model=RAGFileUploadResponse)
async def upload_rag_file(
    agent_id: str,
    user_id: str = Query(..., description="User ID"),
    file: UploadFile = File(..., description="File to upload to RAG store"),
):
    """
    Upload a file to RAG temp directory and trigger upload to Gemini store

    Args:
        agent_id: Agent ID
        user_id: User ID
        file: File to upload

    Returns:
        RAGFileUploadResponse with upload result
    """
    import asyncio

    logger.info(f"Uploading RAG file '{file.filename}' for agent: {agent_id}, user: {user_id}")

    # Supported file formats (docling is disabled, only plain text and PDF are supported)
    SUPPORTED_EXTENSIONS = {'.txt', '.md', '.pdf'}

    # Check file extension
    filename_lower = file.filename.lower() if file.filename else ""
    file_ext = None
    for ext in SUPPORTED_EXTENSIONS:
        if filename_lower.endswith(ext):
            file_ext = ext
            break

    if not file_ext:
        logger.warning(f"Rejected unsupported file format: {file.filename}")
        return RAGFileUploadResponse(
            success=False,
            error=f"Unsupported file format. Only {', '.join(sorted(SUPPORTED_EXTENSIONS))} are supported."
        )

    try:
        # Read file content
        content = await file.read()
        logger.info(f"Uploading RAG file content: {content[:100]}...")
        file_size = len(content)

        # Call service layer to save file
        filepath = RAGFileService.save_file(agent_id, user_id, file.filename, content)

        # Set initial status to pending
        RAGFileService.update_file_status(
            agent_id, user_id, file.filename, "pending",
            extra={"saved_at": str(filepath.stat().st_mtime)}
        )

        # Trigger background upload task
        asyncio.create_task(
            RAGFileService.upload_to_gemini_store(agent_id, user_id, str(filepath), file.filename)
        )

        return RAGFileUploadResponse(
            success=True,
            filename=file.filename,
            size=file_size,
            upload_status="pending",
        )

    except Exception as e:
        logger.error(f"Error uploading RAG file: {e}")
        return RAGFileUploadResponse(
            success=False,
            error=str(e)
        )


@router.delete("/{agent_id}/rag-files/{filename}", response_model=RAGFileDeleteResponse)
async def delete_rag_file(
    agent_id: str,
    filename: str,
    user_id: str = Query(..., description="User ID"),
):
    """
    Delete a RAG file from the temp directory

    Note: This does NOT remove the file from Gemini store (Gemini doesn't support deletion)

    Args:
        agent_id: Agent ID
        filename: Name of the file to delete
        user_id: User ID

    Returns:
        RAGFileDeleteResponse with deletion result
    """
    logger.info(f"Deleting RAG file '{filename}' for agent: {agent_id}, user: {user_id}")

    try:
        # Call service layer to delete file
        deleted = RAGFileService.delete_file(agent_id, user_id, filename)

        if not deleted:
            return RAGFileDeleteResponse(
                success=False,
                error=f"File not found: {filename}"
            )

        return RAGFileDeleteResponse(
            success=True,
            filename=filename,
        )

    except Exception as e:
        logger.error(f"Error deleting RAG file: {e}")
        return RAGFileDeleteResponse(
            success=False,
            error=str(e)
        )


@router.get("/{agent_id}/simple-chat-history", response_model=SimpleChatHistoryResponse)
async def get_simple_chat_history(
    agent_id: str,
    user_id: str = Query(..., description="User ID"),
    limit: int = Query(default=20, description="Maximum number of messages to return (recent N rounds)")
):
    """
    Get simplified chat history between user and Agent

    Queries directly from ChatModule instances, does not rely on Narrative.
    Finds all ChatModule instances by agent_id + user_id to get chat history.

    Query logic:
    1. Find all ChatModule instances by agent_id + user_id
    2. Get messages from instance_json_format_memory_chat table for each instance
    3. Sort by time and return the most recent messages

    Args:
        agent_id: Agent ID
        user_id: User ID
        limit: Maximum number of messages to return (default 20, i.e., last 10 rounds of conversation)

    Returns:
        SimpleChatHistoryResponse with messages
    """
    import json
    from datetime import datetime

    logger.info(f"Getting simple chat history for agent: {agent_id}, user: {user_id}, limit: {limit}")

    try:
        db_client = await get_db_client()
        instance_repo = InstanceRepository(db_client)

        all_messages: List[Dict[str, Any]] = []

        # Find ChatModule instances directly by agent_id + user_id
        # Does not rely on Narrative, fully based on instance data
        all_instances = await instance_repo.get_by_agent_and_user(
            agent_id=agent_id,
            user_id=user_id,
            include_public=False
        )
        # Filter out cancelled and archived Instances
        chat_instances = [
            inst for inst in all_instances
            if inst.module_class == "ChatModule"
            and inst.status not in ("cancelled", "archived")
        ]

        logger.info(f"Found {len(chat_instances)} active ChatModule instances for agent={agent_id}, user={user_id}")

        for instance in chat_instances:
            try:
                memory_row = await db_client.get_one(
                    "instance_json_format_memory_chat",
                    filters={"instance_id": instance.instance_id}
                )

                if memory_row and memory_row.get("memory"):
                    memory_str = memory_row["memory"]
                    memory_data = json.loads(memory_str) if isinstance(memory_str, str) else memory_str
                    messages = memory_data.get("messages", [])

                    # Get associated narrative_id (optional, for frontend display)
                    links = await db_client.get(
                        "instance_narrative_links",
                        filters={"instance_id": instance.instance_id},
                        limit=1
                    )
                    narrative_id = links[0].get("narrative_id") if links else None

                    for msg in messages:
                        meta_data = msg.get("meta_data", {})
                        working_source = meta_data.get("working_source", "chat")
                        role = msg.get("role", "unknown")

                        # Frontend chat history filter rules:
                        # Only show chat-type messages, job/a2a and other types are not displayed
                        if working_source != "chat":
                            continue

                        timestamp = None
                        if "timestamp" in meta_data:
                            timestamp = meta_data["timestamp"]
                        elif "created_at" in msg:
                            timestamp = msg["created_at"]

                        all_messages.append({
                            "role": role,
                            "content": msg.get("content", ""),
                            "timestamp": timestamp,
                            "narrative_id": narrative_id,
                            "instance_id": instance.instance_id,
                            "_sort_key": timestamp or ""
                        })

                    logger.debug(
                        f"Loaded {len(messages)} messages from instance {instance.instance_id}"
                    )
            except Exception as e:
                logger.warning(f"Failed to load chat history from instance {instance.instance_id}: {e}")

        # 4. Sort by time
        def parse_timestamp(ts: str) -> datetime:
            if not ts:
                return datetime.min
            try:
                # Try using fromisoformat (supports ISO 8601 format)
                # Remove timezone identifier 'Z' and replace with '+00:00'
                ts_normalized = ts.replace('Z', '+00:00')
                try:
                    dt = datetime.fromisoformat(ts_normalized)
                    # Convert to naive datetime (remove timezone info) for comparison
                    if dt.tzinfo is not None:
                        dt = dt.replace(tzinfo=None)
                    return dt
                except (ValueError, AttributeError):
                    pass

                # Try common date formats
                for fmt in [
                    "%Y-%m-%d %H:%M:%S.%f",
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%dT%H:%M:%S.%f",
                    "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%d %H:%M:%S.%f%z",
                    "%Y-%m-%dT%H:%M:%S.%f%z",
                ]:
                    try:
                        dt = datetime.strptime(ts, fmt)
                        # Convert to naive datetime (remove timezone info) for comparison
                        if dt.tzinfo is not None:
                            dt = dt.replace(tzinfo=None)
                        return dt
                    except ValueError:
                        continue

                logger.warning(f"Unable to parse timestamp: {ts}")
                return datetime.min
            except Exception as e:
                logger.warning(f"Error parsing timestamp {ts}: {e}")
                return datetime.min

        all_messages.sort(key=lambda m: parse_timestamp(m.get("_sort_key", "")))

        # Debug log: show timestamps of first and last messages after sorting
        if all_messages:
            logger.debug(f"First message timestamp: {all_messages[0].get('_sort_key', 'N/A')}")
            logger.debug(f"Last message timestamp: {all_messages[-1].get('_sort_key', 'N/A')}")

        # 5. Apply limit, return most recent messages
        total_count = len(all_messages)
        if limit > 0 and total_count > limit:
            all_messages = all_messages[-limit:]

        # 6. Build response
        response_messages = [
            SimpleChatMessage(
                role=msg["role"],
                content=msg["content"],
                timestamp=msg.get("timestamp"),
                narrative_id=msg.get("narrative_id")
            )
            for msg in all_messages
        ]

        logger.info(f"Returning {len(response_messages)} messages (total: {total_count})")

        return SimpleChatHistoryResponse(
            success=True,
            messages=response_messages,
            total_count=total_count
        )

    except Exception as e:
        logger.error(f"Error getting simple chat history: {e}")
        import traceback
        traceback.print_exc()
        return SimpleChatHistoryResponse(
            success=False,
            error=str(e)
        )
