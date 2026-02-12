"""
@file_name: skills.py
@author: NetMind.AI
@date: 2026-02-03
@description: REST API routes for skills management

Provides endpoints for:
- GET /api/skills - List skills
- POST /api/skills/install - Install a skill (zip upload or GitHub)
- DELETE /api/skills/{skill_name} - Remove a skill
- PUT /api/skills/{skill_name}/disable - Disable a skill
- PUT /api/skills/{skill_name}/enable - Enable a skill
- GET /api/skills/{skill_name} - Get skill details
- POST /api/skills/{skill_name}/study - Trigger skill study
- GET /api/skills/{skill_name}/study - Get skill study status
"""

import asyncio
import shutil
import tempfile
import traceback
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query, UploadFile, File, Form, HTTPException
from loguru import logger

from xyz_agent_context.utils.db_factory import get_db_client
from xyz_agent_context.module.skill_module import SkillModule
from xyz_agent_context.schema.skill_schema import (
    SkillInfo,
    SkillListResponse,
    SkillOperationResponse,
    SkillStudyResponse,
)


router = APIRouter()


def _get_skill_module(agent_id: str, user_id: str) -> SkillModule:
    """Create a SkillModule instance"""
    return SkillModule(agent_id=agent_id, user_id=user_id, database_client=None)


# =========================================================================
# Background study tasks
# =========================================================================

async def _run_skill_study(
    agent_id: str,
    user_id: str,
    skill_name: str,
    skill_path: str,
) -> None:
    """
    Background logic for Agent to study a Skill

    Build study message -> Run AgentRuntime -> Collect final_output -> Save to .skill_meta.json
    """
    # Lazy import to avoid circular dependencies
    from xyz_agent_context.agent_runtime import AgentRuntime
    from xyz_agent_context.schema import WorkingSource, AgentToolCall
    from xyz_agent_context.repository import MCPRepository

    input_content = (
        f"Please study the skill '{skill_name}' located at {skill_path}.\n\n"
        f"## Step 1: Read & Understand\n"
        f"Read {skill_path}/SKILL.md thoroughly. Understand what this skill does, "
        f"what APIs it provides, and how it works.\n\n"
        f"## Step 2: Registration & Activation (if applicable)\n"
        f"If this skill involves a platform, competition, or external service that requires "
        f"registration or account setup, complete the registration process. "
        f"Save any credentials (API keys, tokens, etc.) securely in {skill_path}/.\n\n"
        f"## Step 3: Set Up Scheduled Jobs (if applicable)\n"
        f"Check if the skill directory contains a HEARTBEAT.md or similar periodic-task guide "
        f"(e.g., heartbeat, polling, check-in, periodic sync). "
        f"If it does, this likely means the skill requires recurring background work — "
        f"such as checking for new competitions, polling game state, submitting periodic actions, etc.\n\n"
        f"**For platform/competition/arena-type skills that have periodic tasks:**\n"
        f"Use your `job_create` tool to set up the appropriate scheduled jobs. For example:\n"
        f"- A heartbeat check-in → `scheduled` job with a suitable cron/interval\n"
        f"- Polling for new competitions → `scheduled` job\n"
        f"- Any recurring workflow described in the heartbeat doc → `scheduled` or `ongoing` job\n\n"
        f"Read the heartbeat/periodic doc carefully and translate each recurring task into "
        f"a concrete job with the right `trigger_config`, `payload`, and `job_type`.\n\n"
        f"**Note:** Pure capability skills (e.g., a coding helper, a translation tool) "
        f"that don't involve external platforms or periodic operations do NOT need scheduled jobs. "
        f"Only create jobs when the skill genuinely requires background recurring work.\n\n"
        f"## Step 4: Summarize\n"
        f"After studying, provide a summary covering:\n"
        f"- What this skill does (core capabilities)\n"
        f"- Any accounts/registrations you completed\n"
        f"- Any scheduled jobs you created (with their schedules and purposes)\n"
        f"- Any pending actions that require human intervention (e.g., Twitter verification)"
    )

    skill_module = _get_skill_module(agent_id, user_id)

    try:
        # Load MCP URLs (same logic as websocket.py)
        mcp_urls = {}
        try:
            db_client = await get_db_client()
            mcp_repo = MCPRepository(db_client)
            mcps = await mcp_repo.get_mcps_by_agent_user(
                agent_id=agent_id,
                user_id=user_id,
                is_enabled=True
            )
            mcp_urls = {mcp.name: mcp.url for mcp in mcps}
        except Exception as e:
            logger.warning(f"Failed to load MCP URLs for skill study: {e}")

        # Run AgentRuntime, collect results
        study_result = ""
        async with AgentRuntime() as runtime:
            async for message in runtime.run(
                agent_id=agent_id,
                user_id=user_id,
                input_content=input_content,
                working_source=WorkingSource.SKILL_STUDY,
                pass_mcp_urls=mcp_urls,
            ):
                # Extract content from AgentToolCall's send_message_to_user_directly
                if isinstance(message, AgentToolCall):
                    if message.tool_name.endswith('send_message_to_user_directly'):
                        study_result = message.tool_input.get('content', '')

        # Fallback handling
        if not study_result:
            study_result = "Study completed. No explicit summary was provided by the agent."

        skill_module.set_study_status(skill_name, "completed", result=study_result)
        logger.info(f"Skill study completed for '{skill_name}'")

    except Exception as e:
        logger.error(f"Skill study failed for '{skill_name}': {e}")
        logger.error(traceback.format_exc())
        skill_module.set_study_status(skill_name, "failed", error=str(e))


# =========================================================================
# API Endpoints
# =========================================================================

@router.get("", response_model=SkillListResponse)
async def list_skills(
    agent_id: str = Query(..., description="Agent ID"),
    user_id: str = Query(..., description="User ID"),
    include_disabled: bool = Query(False, description="Whether to include disabled Skills"),
):
    """Get skill list"""
    logger.info(f"GET /api/skills - agent_id={agent_id}, user_id={user_id}")

    try:
        skill_module = _get_skill_module(agent_id, user_id)
        skills = skill_module.list_skills(include_disabled=include_disabled)

        return SkillListResponse(skills=skills, total=len(skills))

    except Exception as e:
        logger.error(f"Failed to list skills: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/install", response_model=SkillOperationResponse)
async def install_skill(
    agent_id: str = Form(..., description="Agent ID"),
    user_id: str = Form(..., description="User ID"),
    source: str = Form(..., description="Install source: github or zip"),
    url: Optional[str] = Form(None, description="GitHub URL (required when source=github)"),
    branch: str = Form("main", description="Git branch (effective when source=github)"),
    file: Optional[UploadFile] = File(None, description="Zip file (required when source=zip)"),
):
    """
    Install a Skill

    Supports two installation methods:
    1. Install from GitHub: source=github, url=repository URL
    2. Upload zip file: source=zip, file=zip file
    """
    logger.info(
        f"POST /api/skills/install - agent_id={agent_id}, user_id={user_id}, source={source}"
    )

    if source not in ["github", "zip"]:
        raise HTTPException(status_code=400, detail="source must be 'github' or 'zip'")

    if source == "github" and not url:
        raise HTTPException(status_code=400, detail="url is required when source=github")

    if source == "zip" and not file:
        raise HTTPException(status_code=400, detail="file is required when source=zip")

    try:
        skill_module = _get_skill_module(agent_id, user_id)
        skill_info: SkillInfo

        if source == "github":
            skill_info = skill_module.install_from_github(url=url, branch=branch)
        else:
            # Save uploaded file to temporary directory
            temp_dir = Path(tempfile.mkdtemp())
            try:
                zip_path = temp_dir / file.filename
                with open(zip_path, "wb") as f:
                    content = await file.read()
                    f.write(content)

                skill_info = skill_module.install_skill(zip_file_path=zip_path)
            finally:
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)

        return SkillOperationResponse(
            success=True,
            message=f"Skill '{skill_info.name}' installed successfully",
            skill=skill_info
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to install skill: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{skill_name}", response_model=SkillOperationResponse)
async def remove_skill(
    skill_name: str,
    agent_id: str = Query(..., description="Agent ID"),
    user_id: str = Query(..., description="User ID"),
):
    """Remove a Skill"""
    logger.info(f"DELETE /api/skills/{skill_name} - agent_id={agent_id}, user_id={user_id}")

    try:
        skill_module = _get_skill_module(agent_id, user_id)
        success = skill_module.remove_skill(skill_name=skill_name)

        if not success:
            raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")

        return SkillOperationResponse(
            success=True,
            message=f"Skill '{skill_name}' removed successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to remove skill: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{skill_name}/disable", response_model=SkillOperationResponse)
async def disable_skill(
    skill_name: str,
    agent_id: str = Query(..., description="Agent ID"),
    user_id: str = Query(..., description="User ID"),
):
    """Disable a Skill"""
    logger.info(f"PUT /api/skills/{skill_name}/disable - agent_id={agent_id}, user_id={user_id}")

    try:
        skill_module = _get_skill_module(agent_id, user_id)
        success = skill_module.disable_skill(skill_name=skill_name)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Skill '{skill_name}' not found or already disabled"
            )

        return SkillOperationResponse(
            success=True,
            message=f"Skill '{skill_name}' disabled successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to disable skill: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{skill_name}/enable", response_model=SkillOperationResponse)
async def enable_skill(
    skill_name: str,
    agent_id: str = Query(..., description="Agent ID"),
    user_id: str = Query(..., description="User ID"),
):
    """Enable a Skill"""
    logger.info(f"PUT /api/skills/{skill_name}/enable - agent_id={agent_id}, user_id={user_id}")

    try:
        skill_module = _get_skill_module(agent_id, user_id)
        success = skill_module.enable_skill(skill_name=skill_name)

        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Skill '{skill_name}' not found in disabled list"
            )

        return SkillOperationResponse(
            success=True,
            message=f"Skill '{skill_name}' enabled successfully"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to enable skill: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================================
# Study-related Endpoints (must be placed before /{skill_name} to avoid path conflicts)
# Note: FastAPI matches by registration order, but more specific paths are used here
# /{skill_name}/study is more specific than /{skill_name}, so no conflict occurs
# =========================================================================

@router.post("/{skill_name}/study", response_model=SkillStudyResponse)
async def study_skill(
    skill_name: str,
    agent_id: str = Query(..., description="Agent ID"),
    user_id: str = Query(..., description="User ID"),
):
    """
    Trigger Agent to study a Skill

    1. Verify the Skill exists
    2. Set study_status = "studying"
    3. Start background task to run AgentRuntime
    4. Background task automatically updates study_status and study_result upon completion
    """
    logger.info(f"POST /api/skills/{skill_name}/study - agent_id={agent_id}, user_id={user_id}")

    try:
        skill_module = _get_skill_module(agent_id, user_id)
        skill = skill_module.get_skill(skill_name)

        if not skill:
            raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")

        # Check if already studying
        study_info = skill_module.get_study_status(skill_name)
        if study_info["study_status"] == "studying":
            return SkillStudyResponse(
                success=False,
                message="Already studying",
                study_status="studying"
            )

        # Set status to studying
        skill_module.set_study_status(skill_name, "studying")

        # Start background task
        asyncio.create_task(_run_skill_study(
            agent_id=agent_id,
            user_id=user_id,
            skill_name=skill_name,
            skill_path=skill.path,
        ))

        return SkillStudyResponse(
            success=True,
            message="Study started",
            study_status="studying"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start skill study: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{skill_name}/study", response_model=SkillStudyResponse)
async def get_study_status(
    skill_name: str,
    agent_id: str = Query(..., description="Agent ID"),
    user_id: str = Query(..., description="User ID"),
):
    """Get Skill study status (for frontend polling)"""
    try:
        skill_module = _get_skill_module(agent_id, user_id)
        study_info = skill_module.get_study_status(skill_name)

        return SkillStudyResponse(
            success=True,
            study_status=study_info.get("study_status", "idle"),
            study_result=study_info.get("study_result"),
        )

    except Exception as e:
        logger.error(f"Failed to get study status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{skill_name}", response_model=SkillOperationResponse)
async def get_skill(
    skill_name: str,
    agent_id: str = Query(..., description="Agent ID"),
    user_id: str = Query(..., description="User ID"),
):
    """Get Skill details"""
    logger.info(f"GET /api/skills/{skill_name} - agent_id={agent_id}, user_id={user_id}")

    try:
        skill_module = _get_skill_module(agent_id, user_id)
        skill = skill_module.get_skill(skill_name)

        if not skill:
            raise HTTPException(status_code=404, detail=f"Skill '{skill_name}' not found")

        return SkillOperationResponse(success=True, skill=skill)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get skill: {e}")
        raise HTTPException(status_code=500, detail=str(e))
