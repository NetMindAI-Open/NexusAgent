"""
Job Trigger - Background Task Executor

@file_name: job_trigger.py
@author: NetMind.AI
@date: 2025-11-25
@updated: 2026-01-15 (Feature 3.1 - Context Loading Enhancement)
@description: Background polling service for job execution

=============================================================================
Overview
=============================================================================

JobTrigger is a background service that:
1. Polls the database for jobs that are due for execution
2. Builds execution prompts with enriched context (Feature 3.1) and calls AgentRuntime
3. Writes results to user's Inbox via ChatModule
4. Updates job status and execution records

Feature 3.1 Enhancement (2026-01-15):
- Loads Social Network context (related entities information)
- Loads Narrative Summary (overall progress, includes conversation history summary)
- Loads Dependency Outputs (existing feature, maintained)

Execution Flow:
    ┌─────────────────────────────────────────────────────────────────────┐
    │                        JobTrigger Loop                               │
    │                                                                      │
    │   1. Poll DB for due jobs (next_run_time <= now, status = PENDING/ACTIVE)
    │   2. For each job:                                                   │
    │      a. Update status to RUNNING                                     │
    │      b. Build execution prompt from job payload                      │
    │      c. Call AgentRuntime.run()                                      │
    │      d. Write result to Inbox                                        │
    │      e. Update job status and next_run_time                          │
    │   3. Sleep for poll_interval seconds                                 │
    │   4. Repeat                                                          │
    └─────────────────────────────────────────────────────────────────────┘

Architecture:
    ┌─────────────────────────────────────────────────────────────────────┐
    │                         ModuleRunner                                 │
    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐ │
    │  │  A2A API    │  │  MCP        │  │  MCP        │  │  Job       │ │
    │  │  Server     │  │  Modules    │  │  Job Module │  │  Trigger   │ │
    │  └─────────────┘  └─────────────┘  └─────────────┘  └─────┬──────┘ │
    └───────────────────────────────────────────────────────────┼────────┘
                                                                │
                                                                ▼
                                                    ┌─────────────────┐
                                                    │  AgentRuntime   │
                                                    └─────────────────┘

Usage:
    # Standalone
    uv run python -m xyz_agent_context.module.job_module.job_trigger

    # With custom interval
    uv run python -m xyz_agent_context.module.job_module.job_trigger --interval 30
"""

import asyncio
import argparse
from typing import List, Optional, Dict, Any, Set
from uuid import uuid4

from loguru import logger

# Schema
from xyz_agent_context.schema.job_schema import (
    JobModel,
    JobStatus,
    JobType,
    TriggerConfig,
)
from xyz_agent_context.schema.inbox_schema import (
    InboxMessageType,
)
from xyz_agent_context.schema.runtime_message import (
    MessageType,
)
from xyz_agent_context.schema.hook_schema import WorkingSource

# Utils
from xyz_agent_context.utils import DatabaseClient, get_db_client, utc_now, format_for_llm

# Repository
from xyz_agent_context.repository import JobRepository, InboxRepository, UserRepository
from xyz_agent_context.repository.job_repository import calculate_next_run_time

# Prompts
from xyz_agent_context.module.job_module.prompts import (
    JOB_TASK_INFO_TEMPLATE,
    JOB_ENTITIES_SECTION_TEMPLATE,
    JOB_PROGRESS_SECTION_TEMPLATE,
    JOB_DEPENDENCIES_SECTION_TEMPLATE,
    JOB_EXECUTION_PROMPT_TEMPLATE,
)


class JobTrigger:
    """
    Job Trigger - Background Polling Service

    Core responsibilities:
    1. Periodically poll the database to find jobs due for execution
    2. Build execution Prompt and call AgentRuntime
    3. Process execution results and write to Inbox
    4. Update Job status and next execution time

    Lifecycle:
    1. ModuleRunner creates JobTrigger instance
    2. Calls start() in an independent process to begin polling
    3. Calls stop() for graceful shutdown when receiving termination signal
    """

    # =========================================================================
    # Initialization
    # =========================================================================

    def __init__(
        self,
        poll_interval: int = 60,
        job_timeout_minutes: int = 30,
        max_workers: int = 5,
        database_client: Optional[DatabaseClient] = None
    ):
        """
        Initialize JobTrigger

        Args:
            poll_interval: Polling interval (seconds), default 60 seconds
            job_timeout_minutes: Job timeout (minutes), default 30 minutes
            max_workers: Maximum concurrent worker count, default 5
            database_client: Database client (optional, lazy-loaded if not provided)
        """
        self.poll_interval = poll_interval
        self.job_timeout_minutes = job_timeout_minutes
        self.max_workers = max_workers
        self._db = database_client  # May be None, lazy-loaded
        self.running = False

        # Repository (lazy initialization)
        self._job_repo: Optional[JobRepository] = None
        self._inbox_repo: Optional[InboxRepository] = None

        # Worker Pool related
        self._job_queue: asyncio.Queue[JobModel] = asyncio.Queue()
        self._running_jobs: Set[str] = set()  # Set of currently executing job_ids, prevents duplicate enqueue
        self._workers: List[asyncio.Task] = []
        self._poller_task: Optional[asyncio.Task] = None

        logger.info(
            f"JobTrigger initialized: poll_interval={poll_interval}s, "
            f"timeout={job_timeout_minutes}min, max_workers={max_workers}"
        )

    @property
    def db(self) -> DatabaseClient:
        """Get database client (must be used after start())"""
        if self._db is None:
            raise RuntimeError("Database client not initialized. Call start() first.")
        return self._db

    def _get_job_repo(self) -> JobRepository:
        """Get or create JobRepository instance"""
        if self._job_repo is None:
            self._job_repo = JobRepository(self.db)
        return self._job_repo

    def _get_inbox_repo(self) -> InboxRepository:
        """Get or create InboxRepository instance"""
        if self._inbox_repo is None:
            self._inbox_repo = InboxRepository(self.db)
        return self._inbox_repo

    async def _get_user_timezone(self, user_id: str) -> str:
        """
        Get user's timezone setting

        Args:
            user_id: User ID

        Returns:
            User timezone string (IANA format), returns "UTC" if user does not exist
        """
        try:
            user_repo = UserRepository(self.db)
            return await user_repo.get_user_timezone(user_id)
        except Exception as e:
            logger.warning(f"Failed to get user timezone (user_id={user_id}): {e}, using default UTC")
            return "UTC"

    # =========================================================================
    # Lifecycle Management
    # =========================================================================

    async def start(self) -> None:
        """
        Start JobTrigger (Worker Pool mode)

        Architecture:
        - 1 Poller coroutine: periodically queries tasks and puts them in queue
        - N Worker coroutines: takes tasks from queue and executes them

        This is JobTrigger's main entry point, runs continuously until stop() is called.
        """
        # Initialize database client in async context
        if self._db is None:
            self._db = await get_db_client()
            logger.info("Database client initialized in async context")

        logger.info("=" * 60)
        logger.info("🚀 JobTrigger starting (Worker Pool mode)...")
        logger.info(f"   Poll interval: {self.poll_interval} seconds")
        logger.info(f"   Max workers: {self.max_workers}")
        logger.info(f"   Job timeout: {self.job_timeout_minutes} minutes")
        logger.info("=" * 60)

        # Startup recovery: when new process starts, recover all running jobs to schedulable state
        # Because after old process was killed, execution of these jobs must have been interrupted
        repo = self._get_job_repo()
        recovered = await repo.recover_all_running_jobs()
        if recovered > 0:
            logger.warning(f"🔄 Startup recovery: recovered {recovered} stuck running jobs")

        self.running = True

        # Start Workers
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(i))
            self._workers.append(worker)
            logger.debug(f"Worker {i} started")

        # Start Poller
        self._poller_task = asyncio.create_task(self._poller())
        logger.debug("Poller started")

        # Wait for all tasks to complete (usually terminated by stop())
        try:
            await asyncio.gather(self._poller_task, *self._workers)
        except asyncio.CancelledError:
            logger.info("JobTrigger tasks cancelled")

        logger.info("JobTrigger stopped")

    async def stop(self) -> None:
        """
        Gracefully stop JobTrigger

        1. Set running=False to stop poller from enqueuing
        2. Wait for queued tasks to be processed
        3. Cancel all workers
        """
        logger.info("Stopping JobTrigger gracefully...")
        self.running = False

        # Wait for queue to drain (max 30 seconds)
        try:
            await asyncio.wait_for(self._job_queue.join(), timeout=30)
            logger.info("All queued jobs completed")
        except asyncio.TimeoutError:
            logger.warning("Timeout waiting for queue to empty, forcing shutdown")

        # Cancel poller
        if self._poller_task:
            self._poller_task.cancel()

        # Cancel all workers
        for worker in self._workers:
            worker.cancel()

        # Wait for all task cancellations to complete
        await asyncio.gather(
            self._poller_task,
            *self._workers,
            return_exceptions=True
        )

        self._workers.clear()
        self._poller_task = None
        logger.info("JobTrigger shutdown complete")

    # =========================================================================
    # Worker Pool Core
    # =========================================================================

    async def _poller(self) -> None:
        """
        Poller coroutine: periodically queries tasks and puts them in queue

        Responsibilities:
        1. Recover stuck tasks
        2. Query due tasks
        3. Put tasks into queue (skip already executing ones)
        """
        while self.running:
            try:
                await self._poll_and_enqueue()
                await asyncio.sleep(self.poll_interval)
            except asyncio.CancelledError:
                logger.debug("Poller cancelled")
                break
            except Exception as e:
                logger.error(f"Poller error: {e}")
                await asyncio.sleep(self.poll_interval)

    async def _worker(self, worker_id: int) -> None:
        """
        Worker coroutine: takes tasks from queue and executes them

        Args:
            worker_id: Worker number (for logging)
        """
        logger.debug(f"Worker {worker_id} ready")

        while True:
            try:
                # Get task from queue (blocking wait)
                job = await self._job_queue.get()

                try:
                    logger.info(f"[Worker {worker_id}] Executing job: {job.job_id}")
                    await self._execute_job(job)
                finally:
                    # Mark task as done
                    self._job_queue.task_done()
                    # Remove from running set
                    self._running_jobs.discard(job.job_id)

            except asyncio.CancelledError:
                logger.debug(f"Worker {worker_id} cancelled")
                break
            except Exception as e:
                logger.error(f"[Worker {worker_id}] Unexpected error: {e}")

    async def _poll_and_enqueue(self) -> None:
        """
        Execute one polling cycle and enqueue tasks

        1. Recover stuck tasks
        2. Query due tasks
        3. Put tasks into queue (skip already executing ones)
        """
        logger.debug(f"Polling for due jobs at {utc_now()}")

        try:
            repo = self._get_job_repo()

            # 1. First recover stuck tasks
            recovered = await repo.recover_stuck_jobs(
                timeout_minutes=self.job_timeout_minutes
            )
            if recovered > 0:
                logger.info(f"Recovered {recovered} stuck jobs")

            # 2. Query jobs due for execution
            due_jobs = await repo.get_due_jobs()

            if not due_jobs:
                logger.debug("No due jobs found")
                return

            # 3. Put tasks into queue (skip already executing ones)
            enqueued = 0
            for job in due_jobs:
                if job.job_id not in self._running_jobs:
                    self._running_jobs.add(job.job_id)
                    await self._job_queue.put(job)
                    enqueued += 1
                else:
                    logger.debug(f"Job {job.job_id} already running, skipped")

            if enqueued > 0:
                logger.info(f"Enqueued {enqueued} jobs (queue size: {self._job_queue.qsize()})")

        except Exception as e:
            logger.error(f"Error in poll_and_enqueue: {e}")

    async def _get_due_jobs(self) -> List[JobModel]:
        """
        Query jobs that are due for execution.

        Finds jobs where:
        - next_run_time <= now()
        - status in (PENDING, ACTIVE)

        Returns:
            List of JobModel instances ready for execution
        """
        try:
            return await self._get_job_repo().get_due_jobs()
        except Exception as e:
            logger.error(f"Error getting due jobs: {e}")
            return []

    # =========================================================================
    # Job Execution
    # =========================================================================

    async def _update_job_status(
        self,
        job_id: str,
        status: JobStatus,
        error_message: Optional[str] = None
    ) -> int:
        """
        Update Job status

        Args:
            job_id: Job ID
            status: New status
            error_message: Error message (optional)

        Returns:
            Number of affected rows
        """
        return await self._get_job_repo().update_job_status(
            job_id=job_id,
            status=status,
            error_message=error_message
        )

    async def _update_instance_for_execution(self, instance_id: str) -> None:
        """
        Update Instance status to in_progress (for ModulePoller detection)

        Sets:
        - status = 'in_progress'
        - last_polled_status = 'in_progress'
        - callback_processed = False

        Args:
            instance_id: Instance ID
        """
        try:
            query = """
                UPDATE module_instances
                SET status = 'in_progress',
                    last_polled_status = 'in_progress',
                    callback_processed = FALSE,
                    updated_at = NOW()
                WHERE instance_id = %s
            """
            await self.db.execute(query, (instance_id,))
            logger.debug(f"Updated instance {instance_id} for execution (status=in_progress)")
        except Exception as e:
            logger.error(f"Error updating instance {instance_id} for execution: {e}")

    async def _update_instance_completed(self, instance_id: str) -> None:
        """
        Update Instance status to completed (triggers ModulePoller detection)

        Sets:
        - status = 'completed'
        - completed_at = NOW()
        (Preserves last_polled_status = 'in_progress' for Poller change detection)

        Args:
            instance_id: Instance ID
        """
        try:
            query = """
                UPDATE module_instances
                SET status = 'completed',
                    completed_at = NOW(),
                    updated_at = NOW()
                WHERE instance_id = %s
            """
            await self.db.execute(query, (instance_id,))
            logger.debug(f"Updated instance {instance_id} to completed")
        except Exception as e:
            logger.error(f"Error updating instance {instance_id} to completed: {e}")

    async def _update_instance_failed(self, instance_id: str) -> None:
        """
        Update Instance status to failed

        Args:
            instance_id: Instance ID
        """
        try:
            query = """
                UPDATE module_instances
                SET status = 'failed',
                    completed_at = NOW(),
                    updated_at = NOW()
                WHERE instance_id = %s
            """
            await self.db.execute(query, (instance_id,))
            logger.debug(f"Updated instance {instance_id} to failed")
        except Exception as e:
            logger.error(f"Error updating instance {instance_id} to failed: {e}")

    async def _execute_job(self, job: JobModel) -> None:
        """
        Execute a single Job (Feature 3.1 Enhanced)

        Execution flow:
        1. Try to acquire execution lock (atomic operation, prevents duplicate execution)
        2. Build execution Prompt (with full context)
           - Social Network information (related_entity_id)
           - Narrative Summary (overall progress, includes conversation history summary)
           - Dependency Outputs (prerequisite task results)
        3. Call AgentRuntime (using related_entity_id as user_id)
        4. Process execution results
        5. Write to Inbox (notify job.user_id original requester)
        6. Update Job status and next execution time

        Args:
            job: Job to execute
        """
        logger.info(f"Executing job: {job.job_id} - {job.title}")

        try:
            # 1. Try to atomically acquire execution lock (status: PENDING/ACTIVE -> RUNNING)
            # This prevents multiple Workers from executing the same Job simultaneously
            acquired = await self._get_job_repo().try_acquire_job(job.job_id)
            if not acquired:
                logger.warning(f"Failed to acquire lock for job {job.job_id}, skipping")
                return

            # 1.5 Update associated Instance status (for ModulePoller detection)
            if job.instance_id:
                await self._update_instance_for_execution(job.instance_id)

            # 2. Build execution Prompt (including dependency Job outputs)
            prompt = await self._build_execution_prompt(job)
            logger.debug(f"Built prompt for job {job.job_id}: {prompt[:100]}...")

            # 3. Call AgentRuntime
            # Agent will send report to user via agent_send_content_to_user_inbox after task execution
            result = await self._run_agent(job, prompt)

            # 4. Update Job status
            await self._finalize_job_execution(job, result)

            logger.info(f"Job {job.job_id} executed successfully")

        except Exception as e:
            logger.error(f"Error executing job {job.job_id}: {e}")
            await self._handle_job_failure(job, str(e))

    async def _get_dependency_outputs(self, instance_id: str) -> List[Dict[str, Any]]:
        """
        Get execution outputs of dependency Jobs

        Queries module_instances.dependencies via instance_id,
        then retrieves execution results of each dependency Job.

        Args:
            instance_id: Current Job's instance_id

        Returns:
            List of dependency Job outputs, each element contains:
            - instance_id: Dependency's instance_id
            - title: Job title
            - output: Complete execution output
            - status: Execution status
        """
        import json

        outputs = []

        try:
            # 1. Get dependency list of current instance
            query = """
                SELECT dependencies FROM module_instances WHERE instance_id = %s
            """
            rows = await self.db.execute(query, (instance_id,), fetch=True)
            if not rows or not rows[0].get('dependencies'):
                return outputs

            deps_raw = rows[0]['dependencies']
            if isinstance(deps_raw, str):
                dep_ids = json.loads(deps_raw)
            else:
                dep_ids = deps_raw

            if not dep_ids:
                return outputs

            logger.debug(f"Found {len(dep_ids)} dependencies for {instance_id}: {dep_ids}")

            # 2. Get execution output of each dependency
            for dep_id in dep_ids:
                try:
                    # 2.1 Get dependency Job info and process (event_ids)
                    query = """
                        SELECT ij.title, ij.status, ij.process, mi.status as instance_status
                        FROM instance_jobs ij
                        LEFT JOIN module_instances mi ON ij.instance_id = mi.instance_id
                        WHERE ij.instance_id = %s
                    """
                    job_rows = await self.db.execute(query, (dep_id,), fetch=True)
                    if not job_rows:
                        logger.warning(f"Dependency job not found: {dep_id}")
                        continue

                    job_row = job_rows[0]
                    process_raw = job_row.get('process')

                    # 2.2 Get event_id from process
                    event_ids = []
                    if process_raw:
                        if isinstance(process_raw, str):
                            event_ids = json.loads(process_raw)
                        else:
                            event_ids = process_raw

                    # 2.3 Get latest event output
                    output_text = ""
                    if event_ids:
                        latest_event_id = event_ids[-1]  # Get the latest
                        event_query = """
                            SELECT final_output FROM events WHERE event_id = %s
                        """
                        event_rows = await self.db.execute(event_query, (latest_event_id,), fetch=True)
                        if event_rows and event_rows[0].get('final_output'):
                            output_text = event_rows[0]['final_output']

                    outputs.append({
                        'instance_id': dep_id,
                        'title': job_row.get('title', dep_id),
                        'status': job_row.get('instance_status', job_row.get('status', 'unknown')),
                        'output': output_text,
                    })

                except Exception as e:
                    logger.error(f"Error fetching dependency output for {dep_id}: {e}")
                    outputs.append({
                        'instance_id': dep_id,
                        'title': dep_id,
                        'status': 'error',
                        'output': f"[Failed to get output: {str(e)}]",
                    })

        except Exception as e:
            logger.error(f"Error getting dependency outputs: {e}")

        return outputs

    async def _load_social_network_context(
        self,
        entity_ids: List[str],
        agent_id: str
    ) -> List[Dict[str, Any]]:
        """
        Load Social Network context (Feature 3.1 Enhancement)

        Loads detailed Entity information for the given entity_ids for Job execution.

        Args:
            entity_ids: List of Entity IDs (may contain only a single related_entity_id)
            agent_id: Agent ID (for querying SocialNetworkModule's instance_id)

        Returns:
            List of Entity information, each element contains:
            - entity_id: Entity ID
            - entity_name: Entity name
            - entity_type: Entity type (user/agent/organization)
            - description: Entity description (truncated to 500 characters)
            - tags: Tag list (max 10)
            - persona: Persona information (truncated to 300 characters)
            - expertise_domains: Expertise domains (max 5)
        """
        if not entity_ids:
            return []

        try:
            from xyz_agent_context.repository import (
                SocialNetworkRepository,
                InstanceRepository
            )

            # 1. Get SocialNetworkModule's instance_id
            instance_repo = InstanceRepository(self.db)
            instances = await instance_repo.get_by_agent(
                agent_id=agent_id,
                module_class="SocialNetworkModule"
            )

            if not instances:
                logger.warning(f"No SocialNetworkModule found for agent {agent_id}")
                return []

            social_instance_id = instances[0].instance_id
            logger.debug(f"Found SocialNetworkModule instance: {social_instance_id}")

            # 2. Query detailed information for each Entity
            social_repo = SocialNetworkRepository(self.db)
            entities_info = []

            for entity_id in entity_ids:
                try:
                    entity = await social_repo.get_entity(entity_id, social_instance_id)
                    if entity:
                        # Truncate overly long fields (avoid prompt being too long)
                        description = entity.entity_description[:500] if entity.entity_description else ""

                        # Extract persona from identity_info (if available)
                        persona = None
                        if entity.identity_info and isinstance(entity.identity_info, dict):
                            persona_raw = entity.identity_info.get('persona', '')
                            if persona_raw:
                                persona = str(persona_raw)[:300]

                        entities_info.append({
                            "entity_id": entity.entity_id,
                            "entity_name": entity.entity_name,
                            "entity_type": entity.entity_type,
                            "description": description,
                            "tags": entity.tags[:10],  # Limit tag count
                            "persona": persona,
                            "expertise_domains": entity.expertise_domains[:5] if entity.expertise_domains else []
                        })
                        logger.debug(f"Loaded entity: {entity.entity_name} ({entity_id})")
                    else:
                        logger.warning(f"Entity {entity_id} not found")
                except Exception as e:
                    logger.error(f"Failed to load entity {entity_id}: {e}")
                    # Continue processing other entities

            logger.info(f"Loaded {len(entities_info)} entities for job context")
            return entities_info

        except Exception as e:
            logger.error(f"Failed to load social network context: {e}")
            return []

    async def _load_narrative_summary(self, narrative_id: str) -> str:
        """
        Load Narrative summary (Feature 3.1 Enhancement)

        Gets the Narrative's current_summary field for understanding overall progress during Job execution.

        Args:
            narrative_id: Narrative ID

        Returns:
            Narrative summary string (truncated to 800 characters)
        """
        if not narrative_id:
            return ""

        try:
            from xyz_agent_context.repository import NarrativeRepository

            narrative_repo = NarrativeRepository(self.db)

            # Query Narrative
            narrative = await narrative_repo.get_by_id(narrative_id)

            if not narrative:
                logger.warning(f"Narrative {narrative_id} not found")
                return ""

            # Extract current_summary
            if narrative.narrative_info and narrative.narrative_info.current_summary:
                summary = narrative.narrative_info.current_summary
                # Truncate overly long summary
                truncated_summary = summary[:800] if len(summary) > 800 else summary
                logger.info(f"Loaded narrative summary for {narrative_id} (length: {len(truncated_summary)})")
                return truncated_summary
            else:
                logger.debug(f"Narrative {narrative_id} has no current_summary")
                return ""

        except Exception as e:
            logger.error(f"Failed to load narrative summary for {narrative_id}: {e}")
            return ""

    async def _build_execution_prompt(self, job: JobModel) -> str:
        """
        Build execution prompt for AgentRuntime (Feature 3.1 Enhanced).

        Combines job metadata with the payload to create a complete,
        self-contained prompt for the Agent to execute.

        Enhancement (Feature 3.1):
        - Loads Social Network context (related entities information)
        - Loads Narrative Summary (overall progress, includes conversation history summary)
        - Loads Dependency Outputs (existing feature)

        Timezone enhancement:
        - Gets user timezone, formats time in user-friendly display format
        - Adds current execution time to Prompt

        Args:
            job: JobModel instance

        Returns:
            Complete execution prompt string with enriched context
        """
        # ===== Get user timezone, format time =====
        user_tz = await self._get_user_timezone(job.user_id)
        current_time_str = format_for_llm(utc_now(), user_tz)
        created_str = format_for_llm(job.created_at, user_tz) if job.created_at else "Unknown"

        # ===== Load all context (Feature 3.1) =====

        # 1. Load Social Network context (single target user)
        entities_info = []
        if job.related_entity_id:
            entities_info = await self._load_social_network_context(
                entity_ids=[job.related_entity_id],  # Convert single value to list
                agent_id=job.agent_id
            )

        # 2. Load Narrative Summary (includes conversation history summary)
        narrative_summary = ""
        if job.narrative_id:
            narrative_summary = await self._load_narrative_summary(
                narrative_id=job.narrative_id
            )

        # 3. Load dependency Job outputs (existing feature)
        dep_outputs = []
        if job.instance_id:
            dep_outputs = await self._get_dependency_outputs(job.instance_id)

        # ===== Build Prompt sections =====

        # Section: Task information
        # Execution identity: use related_entity_id if available, otherwise use job.user_id
        execution_user_id = job.related_entity_id or job.user_id
        task_info_section = JOB_TASK_INFO_TEMPLATE.format(
            title=job.title,
            description=job.description,
            created_str=created_str,
            current_time_str=current_time_str,
            execution_user_id=execution_user_id,
            user_id=job.user_id,
        )

        # Section: Related people/entities
        entities_section = ""
        if entities_info:
            entity_lines = []
            for entity in entities_info:
                entity_line = f"- **{entity['entity_name']}** ({entity['entity_type']})"
                if entity.get('description'):
                    entity_line += f"\n  - Description: {entity['description']}"
                if entity.get('tags'):
                    entity_line += f"\n  - Tags: {', '.join(entity['tags'])}"
                if entity.get('persona'):
                    entity_line += f"\n  - Persona: {entity['persona']}"
                entity_lines.append(entity_line)

            entities_section = JOB_ENTITIES_SECTION_TEMPLATE.format(
                entity_lines=chr(10).join(entity_lines)
            )
            logger.info(f"Added {len(entities_info)} entities to prompt")

        # Section: Current progress (Narrative Summary already includes conversation history summary)
        narrative_section = ""
        if narrative_summary:
            narrative_section = JOB_PROGRESS_SECTION_TEMPLATE.format(
                narrative_summary=narrative_summary
            )
            logger.info("Added narrative summary to prompt")

        # Section: Prerequisite task results
        dependency_section = ""
        if dep_outputs:
            dep_parts = []
            for dep in dep_outputs:
                dep_part = f"""### {dep['title']} (`{dep['instance_id']}`)
**Status**: {dep['status']}

**Execution Output**:
{dep['output'] if dep['output'] else '*This task has no output content*'}
"""
                dep_parts.append(dep_part)

            dependency_section = JOB_DEPENDENCIES_SECTION_TEMPLATE.format(
                dep_parts=chr(10).join(dep_parts)
            )
            logger.info(f"Added {len(dep_outputs)} dependency outputs to prompt")

        # ===== Assemble complete Prompt =====
        extra_requirement = ""
        if dep_outputs or entities_info or narrative_summary:
            extra_requirement = "6. Make full use of prerequisite task results and context information, do not repeat already completed work"

        prompt = JOB_EXECUTION_PROMPT_TEMPLATE.format(
            task_info_section=task_info_section,
            entities_section=entities_section,
            narrative_section=narrative_section,
            dependency_section=dependency_section,
            payload=job.payload,
            related_entity_id=job.related_entity_id,
            extra_requirement=extra_requirement,
        )
        return prompt

    async def _run_agent(self, job: JobModel, prompt: str) -> Dict[str, Any]:
        """
        Execute job using AgentRuntime.

        Creates an AgentRuntime instance and runs the prompt,
        collecting all output for delivery to the user's inbox.

        Args:
            job: JobModel instance
            prompt: Execution prompt

        Returns:
            Dict containing event_id, content, and success status
        """
        event_id = f"event_{uuid4().hex[:12]}"

        try:
            # Import AgentRuntime lazily to avoid circular imports
            from xyz_agent_context.agent_runtime import AgentRuntime

            logger.info(f"[JobTrigger] Starting AgentRuntime for job {job.job_id}")

            # Create AgentRuntime instance
            runtime = AgentRuntime()

            # Collect text output from streaming response
            final_output = []
            tool_calls = []

            # Execution identity: use related_entity_id (if available) as user_id, otherwise use job.user_id
            # This way Job executes in the target user's context, loading their Narrative and related info
            execution_user_id = job.related_entity_id or job.user_id
            logger.info(
                f"[JobTrigger] Executing job {job.job_id} as user_id={execution_user_id} "
                f"(related_entity_id={job.related_entity_id}, job.user_id={job.user_id})"
            )

            async for response in runtime.run(
                agent_id=job.agent_id,
                user_id=execution_user_id,  # Execute as target user identity
                input_content=prompt,
                working_source=WorkingSource.JOB,  # Identifies this as Job-triggered execution (using enum type)
                job_instance_id=job.instance_id,  # Pass instance_id for Hook to locate current Instance
                forced_narrative_id=job.narrative_id,  # Force use of Job-associated Narrative
            ):
                # Collect text deltas (AgentTextDelta)
                if hasattr(response, 'message_type'):
                    if response.message_type == MessageType.AGENT_RESPONSE:
                        if hasattr(response, 'delta') and response.delta:
                            final_output.append(response.delta)

                    # Log tool calls for debugging
                    elif response.message_type == MessageType.TOOL_CALL:
                        if hasattr(response, 'tool_name'):
                            tool_calls.append(response.tool_name)
                            logger.debug(f"[JobTrigger] Tool called: {response.tool_name}")

            # Combine all text chunks
            content = "".join(final_output)

            # Add execution metadata if content is empty
            if not content.strip():
                # Get user timezone, format execution time
                user_tz = await self._get_user_timezone(job.user_id)
                executed_at_str = format_for_llm(utc_now(), user_tz)

                content = f"""## Task Completed: {job.title}

The task was executed but produced no text output.

**Execution Details:**
- Job ID: {job.job_id}
- Executed at: {executed_at_str}
- Tools used: {', '.join(tool_calls) if tool_calls else 'None'}

---
*This message was generated by a scheduled job.*
"""

            logger.info(f"[JobTrigger] AgentRuntime completed for job {job.job_id}, output length: {len(content)}")

            return {
                "event_id": event_id,
                "content": content,
                "success": True,
                "tool_calls": tool_calls,
            }

        except Exception as e:
            logger.exception(f"Error running agent for job {job.job_id}: {e}")

            return {
                "event_id": event_id,
                "content": f"Error executing job: {str(e)}",
                "success": False,
                "error": str(e),
            }

    # =========================================================================
    # Result Processing
    # =========================================================================

    async def _write_to_inbox(self, job: JobModel, result: Dict[str, Any]) -> None:
        """
        Write execution result to user's Inbox.

        Uses ChatModule's inbox capability to deliver job results
        to the user. The message will appear in their Streamlit inbox.

        Args:
            job: JobModel instance
            result: Execution result containing content and event_id
        """
        try:
            # Get user timezone, format timestamp
            user_tz = await self._get_user_timezone(job.user_id)
            timestamp = format_for_llm(utc_now(), user_tz)
            title = f"{job.title} - {timestamp}"

            # Generate message_id
            msg_id = f"msg_{uuid4().hex[:16]}"

            # Create inbox message
            db_id = await self._get_inbox_repo().create_message(
                user_id=job.user_id,
                title=title,
                content=result.get("content", ""),
                message_id=msg_id,
                message_type=InboxMessageType.JOB_RESULT,
                source_type="job",
                source_id=job.job_id,
                event_id=result.get("event_id")
            )

            logger.debug(f"Created inbox message {msg_id} (db_id={db_id}) for job {job.job_id}")

        except Exception as e:
            logger.error(f"Error writing to inbox for job {job.job_id}: {e}")

    async def _finalize_job_execution(
        self,
        job: JobModel,
        result: Dict[str, Any]
    ) -> None:
        """
        Finalize job after successful execution.

        Performs post-execution updates:
        1. Add event_id to process list
        2. Update last_run_time
        3. For one_off: mark as COMPLETED
        4. For scheduled: mark as ACTIVE and calculate next_run_time

        Args:
            job: JobModel instance
            result: Execution result
        """
        try:
            now = utc_now()
            event_id = result.get("event_id")
            repo = self._get_job_repo()

            # Add event to process list
            if event_id:
                await repo.add_event_to_process(
                    job_id=job.job_id,
                    event_id=event_id
                )

            # Handle based on job type
            if job.job_type == JobType.ONE_OFF:
                # One-off job: mark as completed
                await repo.update_job_status(
                    job_id=job.job_id,
                    status=JobStatus.COMPLETED
                )
                # Update Instance status to completed (triggers ModulePoller)
                if job.instance_id:
                    await self._update_instance_completed(job.instance_id)
                logger.info(f"Job {job.job_id} completed (one_off)")

            elif job.job_type == JobType.SCHEDULED:
                # Scheduled job: calculate next run time and mark as active
                next_run = calculate_next_run_time(
                    job_type=job.job_type,
                    trigger_config=job.trigger_config,
                    last_run_time=now,
                )

                await repo.update_next_run_time(
                    job_id=job.job_id,
                    next_run_time=next_run,
                    last_run_time=now
                )

                await repo.update_job_status(
                    job_id=job.job_id,
                    status=JobStatus.ACTIVE
                )

                # Scheduled job also marked as completed after each execution (triggers ModulePoller)
                if job.instance_id:
                    await self._update_instance_completed(job.instance_id)

                next_run_str = next_run.strftime("%Y-%m-%d %H:%M") if next_run else "N/A"
                logger.info(f"Job {job.job_id} rescheduled, next run: {next_run_str}")

            elif job.job_type == JobType.ONGOING:
                # ONGOING job: execute continuously until end_condition is met or max_iterations reached
                # Note: end_condition is primarily checked by hook_after_event_execution (entry point 1)
                # JobTrigger (entry point 2) is only responsible for:
                #   1) Updating iteration_count
                #   2) Checking max_iterations
                #   3) As fallback: only update status and next_run_time when entry point 1 hasn't updated status

                # Get current iteration_count
                current_iteration = job.iteration_count or 0
                new_iteration = current_iteration + 1

                # Check if max_iterations reached
                max_iterations = None
                if job.trigger_config:
                    max_iterations = job.trigger_config.max_iterations

                if max_iterations and new_iteration >= max_iterations:
                    # Reached max iterations, mark as COMPLETED
                    await repo.update_job(job.job_id, {
                        "status": JobStatus.COMPLETED.value,
                        "iteration_count": new_iteration,
                        "last_run_time": now,
                    })
                    if job.instance_id:
                        await self._update_instance_completed(job.instance_id)
                    logger.info(
                        f"Job {job.job_id} completed (ongoing, max_iterations={max_iterations} reached)"
                    )
                else:
                    # Continue execution
                    # First check if entry point 1 (hook_after_event_execution) has already updated the status
                    current_job = await repo.get_job(job.job_id)
                    current_status = current_job.status if current_job else JobStatus.RUNNING

                    # Basic update: iteration_count and last_run_time (entry point 2 exclusive)
                    updates = {
                        "iteration_count": new_iteration,
                        "last_run_time": now,
                    }

                    # Only update status and next_run_time when status is still RUNNING (means entry point 1 failed)
                    if current_status == JobStatus.RUNNING:
                        logger.warning(
                            f"Job {job.job_id}: status still RUNNING after hook, "
                            f"hook may have failed. Falling back to mechanical update."
                        )
                        next_run = calculate_next_run_time(
                            job_type=job.job_type,
                            trigger_config=job.trigger_config,
                            last_run_time=now,
                        )
                        updates["status"] = JobStatus.ACTIVE.value
                        updates["next_run_time"] = next_run
                    else:
                        logger.info(
                            f"Job {job.job_id}: status={current_status.value} (updated by hook), "
                            f"respecting hook's decision."
                        )

                    await repo.update_job(job.job_id, updates)

                    next_run_str = updates.get("next_run_time")
                    next_run_str = next_run_str.strftime("%Y-%m-%d %H:%M") if next_run_str else "N/A (set by hook)"
                    logger.info(
                        f"Job {job.job_id} ongoing, iteration={new_iteration}"
                        f"{f'/{max_iterations}' if max_iterations else ''}, next run: {next_run_str}"
                    )

        except Exception as e:
            logger.error(f"Error finalizing job {job.job_id}: {e}")

    async def _handle_job_failure(self, job: JobModel, error: str) -> None:
        """
        Handle job execution failure.

        Updates job status to FAILED and records the error.
        Optionally sends an error notification to the user's inbox.

        Args:
            job: JobModel instance
            error: Error message
        """
        try:
            # Update job status to FAILED with error message
            await self._get_job_repo().update_job_status(
                job_id=job.job_id,
                status=JobStatus.FAILED,
                error_message=error
            )

            # Update Instance status to failed (triggers ModulePoller)
            if job.instance_id:
                await self._update_instance_failed(job.instance_id)

            logger.warning(f"Job {job.job_id} failed: {error}")

            # Get user timezone, format error time
            user_tz = await self._get_user_timezone(job.user_id)
            error_time_str = format_for_llm(utc_now(), user_tz)

            # Send error notification to user's inbox
            await self._get_inbox_repo().create_message(
                user_id=job.user_id,
                title=f"Job Failed: {job.title}",
                content=f"""## Job Execution Failed

**Job:** {job.title}
**Job ID:** {job.job_id}
**Error:** {error}
**Time:** {error_time_str}

Please check the job configuration and try again.
""",
                message_type=InboxMessageType.JOB_RESULT,
                source_type="job",
                source_id=job.job_id
            )

        except Exception as e:
            logger.error(f"Error handling job failure for {job.job_id}: {e}")


# =============================================================================
# ModuleRunner Integration Entry Point
# =============================================================================

def run_job_trigger(
    poll_interval: int = 60,
    max_workers: int = 5
) -> None:
    """
    Run JobTrigger (called by ModuleRunner)

    This is the process entry function for JobTrigger.
    ModuleRunner calls this function in an independent process.

    Args:
        poll_interval: Polling interval (seconds)
        max_workers: Maximum concurrent worker count
    """
    import xyz_agent_context.settings  # noqa: F401 - Ensure .env is loaded

    # Don't create database client here, let start() lazy-load in async context
    trigger = JobTrigger(
        poll_interval=poll_interval,
        max_workers=max_workers
    )
    asyncio.run(trigger.start())


# =============================================================================
# Standalone Entry Point
# =============================================================================

def main():
    """CLI entry point for JobTrigger."""
    parser = argparse.ArgumentParser(
        description="JobTrigger - Background Task Executor (Worker Pool mode)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start with default settings (60s interval, 5 workers)
  uv run python -m xyz_agent_context.module.job_module.job_trigger

  # Start with 30s interval and 3 workers
  uv run python -m xyz_agent_context.module.job_module.job_trigger --interval 30 --workers 3

  # Run once (for testing)
  uv run python -m xyz_agent_context.module.job_module.job_trigger --once
"""
    )

    parser.add_argument(
        "--interval", "-i",
        type=int,
        default=60,
        help="Poll interval in seconds (default: 60)"
    )

    parser.add_argument(
        "--workers", "-w",
        type=int,
        default=5,
        help="Max concurrent workers (default: 5)"
    )

    parser.add_argument(
        "--once",
        action="store_true",
        help="Run once and exit (for testing)"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )

    args = parser.parse_args()

    # Configure logging level
    if args.debug:
        import sys
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")

    print("=" * 60)
    print("🚀 JobTrigger - Background Task Executor (Worker Pool)")
    print("=" * 60)
    print(f"   Poll interval: {args.interval}s")
    print(f"   Max workers: {args.workers}")
    print(f"   Mode: {'Single run' if args.once else 'Continuous'}")
    print("=" * 60)
    print("\n💡 Press Ctrl+C to stop\n")

    if args.once:
        # Run once for testing (single poll, no worker pool)
        async def run_once():
            import xyz_agent_context.settings  # noqa: F401
            trigger = JobTrigger(
                poll_interval=args.interval,
                max_workers=args.workers
            )
            # Manually initialize database client
            trigger._db = await get_db_client()
            await trigger._poll_and_enqueue()
            print(f"\n✅ Single poll completed, {trigger._job_queue.qsize()} jobs in queue")

        asyncio.run(run_once())
    else:
        # Run continuously with Worker Pool
        run_job_trigger(args.interval, args.workers)


async def test_execute_single_job():
    """
    Test executing a single Job (for development debugging)

    Usage:
        uv run python -c "import asyncio; from xyz_agent_context.module.job_module.job_trigger import test_execute_single_job; asyncio.run(test_execute_single_job())"
    """
    import xyz_agent_context.settings  # noqa: F401 - Ensure .env is loaded

    database_client = await get_db_client()
    trigger = JobTrigger(database_client=database_client)

    # Build test Job
    job = JobModel(
        job_id="job_test_" + uuid4().hex[:8],
        title="AI News Summary Test",
        agent_id="agent_ecb12faf",
        user_id="user_binliang",
        job_type=JobType.ONE_OFF,
        trigger_config=TriggerConfig(run_at=utc_now()),
        description="Test: collect AI domain news and generate summary.",
        payload="Search for today's important AI news, generate a summary report containing 3-5 news items.",
        created_at=utc_now(),
        updated_at=utc_now(),
        status=JobStatus.PENDING,
        next_run_time=utc_now(),
        process=[],
    )

    logger.info(f"Testing job execution: {job.job_id}")
    await trigger._execute_job(job)
    logger.info("Test completed")


if __name__ == "__main__":
    main()
    