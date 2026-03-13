"""
@file_name: matrix_trigger.py
@author: Bin Liang
@date: 2026-03-10
@description: MatrixTrigger — background message polling process

Single-process poller that monitors all Agent Matrix credentials for new messages.
Architecture mirrors JobTrigger: 1 Poller + N Workers.

Flow:
1. Poller iterates over due credentials (next_poll_time <= now)
2. For each, calls NexusMatrix heartbeat endpoint
3. If has_updates, fetches new messages and enqueues them
4. Workers pick up messages and call AgentRuntime.run() for each
5. Results written to Agent Inbox + rooms marked as read
6. Adaptive polling: active agents polled more frequently

Usage:
    # Standalone
    uv run python -m xyz_agent_context.module.matrix_module.matrix_trigger

    # With custom settings
    uv run python -m xyz_agent_context.module.matrix_module.matrix_trigger --workers 3
"""

from __future__ import annotations

import asyncio
import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from loguru import logger

from xyz_agent_context.schema.hook_schema import WorkingSource
from xyz_agent_context.schema.inbox_schema import InboxMessageType
from xyz_agent_context.schema.runtime_message import MessageType
from xyz_agent_context.schema.channel_tag import ChannelTag
from xyz_agent_context.utils import DatabaseClient, get_db_client

from ._matrix_credential_manager import MatrixCredentialManager, MatrixCredential
from .matrix_client import NexusMatrixClient
from .matrix_context_builder import MatrixContextBuilder
from xyz_agent_context.channel.channel_context_builder_base import ChannelHistoryConfig


# === Adaptive polling constants ===
POLL_MIN_INTERVAL = 5    # Seconds — active agent
POLL_MAX_INTERVAL = 60   # Seconds — idle agent
POLL_STEP_UP = 10        # Seconds — increase per idle cycle
POLL_INITIAL = 10        # Seconds — initial interval

# === Safety net: prevent extreme agent-to-agent loops ===
ROOM_RATE_LIMIT_MAX = 100       # Max messages per agent per room in the window
ROOM_RATE_LIMIT_WINDOW = 1800   # Window in seconds (30 min)


@dataclass
class MessageTask:
    """A single message to process, ready for a Worker."""
    credential: MatrixCredential
    room_id: str
    message_event: Dict[str, Any]


class MatrixTrigger:
    """
    Background polling service for Matrix messages.

    Architecture: 1 Poller coroutine + N Worker coroutines.
    Polls all active Agent credentials for new messages via heartbeat,
    then dispatches message processing to the worker pool.

    Args:
        base_poll_interval: Base polling cycle interval in seconds
        max_workers: Max concurrent message processing workers
        history_config: Conversation history loading config
    """

    def __init__(
        self,
        base_poll_interval: int = 10,
        max_workers: int = 5,
        history_config: Optional[ChannelHistoryConfig] = None,
    ):
        self.base_poll_interval = base_poll_interval
        self.max_workers = max_workers
        self.history_config = history_config or ChannelHistoryConfig()

        self._db: Optional[DatabaseClient] = None
        self._cred_mgr: Optional[MatrixCredentialManager] = None

        self.running = False
        self._task_queue: asyncio.Queue[MessageTask] = asyncio.Queue()
        self._processing_agents: Set[str] = set()  # Agents currently being processed
        self._processed_event_ids: Set[str] = set()  # Dedup: recently processed event IDs
        self._max_event_id_cache = 500  # Max cached event IDs before pruning
        # Safety net: track (agent_id, room_id) → list of timestamps
        self._room_activity: Dict[str, List[datetime]] = {}
        self._workers: List[asyncio.Task] = []
        self._poller_task: Optional[asyncio.Task] = None
        # Room metadata cache: room_id → {member_count, creator}
        # Used for DM detection and creator-always-active rule.
        self._room_meta: Dict[str, Dict[str, Any]] = {}

    @property
    def db(self) -> DatabaseClient:
        if self._db is None:
            raise RuntimeError("Database not initialized. Call start() first.")
        return self._db

    @property
    def cred_mgr(self) -> MatrixCredentialManager:
        if self._cred_mgr is None:
            self._cred_mgr = MatrixCredentialManager(self.db)
        return self._cred_mgr

    # =========================================================================
    # Lifecycle
    # =========================================================================

    async def start(self) -> None:
        """
        Start the MatrixTrigger (Worker Pool mode).

        1 Poller + N Workers. Runs until stop() is called.
        """
        if self._db is None:
            self._db = await get_db_client()
            logger.info("MatrixTrigger: database client initialized")

        logger.info("=" * 60)
        logger.info("MatrixTrigger starting (Worker Pool mode)")
        logger.info(f"  Base poll interval: {self.base_poll_interval}s")
        logger.info(f"  Max workers: {self.max_workers}")
        logger.info(f"  History loading: {self.history_config.load_conversation_history}")
        logger.info("=" * 60)

        self.running = True

        # Start workers
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(i))
            self._workers.append(worker)

        # Start poller
        self._poller_task = asyncio.create_task(self._poller())

        try:
            await asyncio.gather(self._poller_task, *self._workers)
        except asyncio.CancelledError:
            logger.info("MatrixTrigger tasks cancelled")

        logger.info("MatrixTrigger stopped")

    async def stop(self) -> None:
        """Gracefully stop the trigger."""
        logger.info("Stopping MatrixTrigger gracefully...")
        self.running = False

        try:
            await asyncio.wait_for(self._task_queue.join(), timeout=30)
        except asyncio.TimeoutError:
            logger.warning("Timeout waiting for queue to drain, forcing shutdown")

        if self._poller_task:
            self._poller_task.cancel()
        for w in self._workers:
            w.cancel()

        await asyncio.gather(
            self._poller_task, *self._workers, return_exceptions=True
        )
        self._workers.clear()
        self._poller_task = None

    def _check_room_rate_limit(self, agent_id: str, room_id: str) -> bool:
        """
        Check if agent has exceeded the safety-net rate limit for a room.

        Returns True if the message should be SKIPPED (rate limited).
        This is a high-threshold safety net (100 msgs / 30 min) — normal
        conversations should never hit this. Its purpose is to prevent
        runaway agent-to-agent loops in extreme edge cases.
        """
        key = f"{agent_id}:{room_id}"
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=ROOM_RATE_LIMIT_WINDOW)

        # Prune old entries
        timestamps = self._room_activity.get(key, [])
        timestamps = [t for t in timestamps if t > cutoff]

        if len(timestamps) >= ROOM_RATE_LIMIT_MAX:
            logger.warning(
                f"Safety net: agent {agent_id} hit rate limit in room {room_id} "
                f"({len(timestamps)} msgs in {ROOM_RATE_LIMIT_WINDOW}s). Skipping."
            )
            self._room_activity[key] = timestamps
            return True

        timestamps.append(now)
        self._room_activity[key] = timestamps
        return False

    def _is_mentioned(self, msg: Dict[str, Any], cred: MatrixCredential) -> bool:
        """
        Check if this agent is mentioned in the message via m.mentions.

        Uses the structured m.mentions field from the Matrix event content:
        - m.mentions.room == True → @everyone, all agents triggered
        - m.mentions.user_ids contains agent's matrix_user_id → that agent triggered
        - No m.mentions at all → not mentioned (skip in group chats)

        Args:
            msg: Message event dict (must contain "content" with full event content)
            cred: The agent's Matrix credential

        Returns:
            True if the agent should process this message
        """
        content = msg.get("content")
        if not isinstance(content, dict):
            return False

        mentions = content.get("m.mentions")
        if not isinstance(mentions, dict):
            return False

        # m.mentions.room == True → @everyone
        if mentions.get("room") is True:
            return True

        # m.mentions.user_ids contains this agent
        mentioned_ids = mentions.get("user_ids", [])
        if isinstance(mentioned_ids, list) and cred.matrix_user_id in mentioned_ids:
            return True

        return False

    async def _get_room_meta(
        self, client: "NexusMatrixClient", api_key: str, room_id: str
    ) -> Dict[str, Any]:
        """
        Get room metadata (cached): member_count + creator.

        Uses in-memory cache to avoid repeated API calls.
        Cache is never invalidated within a session — acceptable because
        room creator never changes and DM rooms rarely change membership.

        Returns:
            {"member_count": int, "creator": str | None}
        """
        if room_id in self._room_meta:
            return self._room_meta[room_id]

        info = await client.get_room_info(api_key=api_key, room_id=room_id)
        meta = {
            "member_count": info.get("member_count", 0) if info else 0,
            "creator": info.get("creator") if info else None,
        }
        self._room_meta[room_id] = meta
        return meta

    # =========================================================================
    # Poller
    # =========================================================================

    async def _poller(self) -> None:
        """Poller coroutine: iterate over due credentials and check for messages."""
        while self.running:
            try:
                await self._poll_cycle()
                await asyncio.sleep(self.base_poll_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Poller error: {e}")
                await asyncio.sleep(self.base_poll_interval)

    async def _poll_cycle(self) -> None:
        """Execute one polling cycle across all due credentials."""
        now = datetime.now(timezone.utc)
        due_creds = await self.cred_mgr.get_due_credentials(now)

        if not due_creds:
            return

        logger.debug(f"Polling {len(due_creds)} due credential(s)")

        for cred in due_creds:
            # Skip if this agent is already being processed (serial per agent)
            if cred.agent_id in self._processing_agents:
                continue

            try:
                await self._check_credential(cred, now)
            except Exception as e:
                logger.error(f"Error checking credential for {cred.agent_id}: {e}")

    async def _check_credential(self, cred: MatrixCredential, now: datetime) -> None:
        """Check a single credential for new messages via heartbeat."""
        client = NexusMatrixClient(server_url=cred.server_url)
        try:
            hb = await client.heartbeat(api_key=cred.api_key)

            # Default: use current interval for next poll
            next_poll = now + timedelta(seconds=POLL_INITIAL)

            try:
                has_activity = False

                # --- Handle pending invitations (auto-accept + trigger runtime) ---
                pending_invites = hb.get("pending_invites", []) if hb else []
                for invite in pending_invites:
                    invite_room_id = invite.get("room_id", "")
                    inviter = invite.get("inviter", "")
                    if not invite_room_id:
                        continue

                    # Auto-accept: join the room
                    joined = await client.join_room(
                        api_key=cred.api_key, room_id=invite_room_id
                    )
                    if joined:
                        logger.info(
                            f"Auto-accepted invite for {cred.agent_id}: "
                            f"room={invite_room_id}, inviter={inviter}"
                        )
                        # Enqueue as an event task so AgentRuntime can react
                        task = MessageTask(
                            credential=cred,
                            room_id=invite_room_id,
                            message_event={
                                "type": "invite",
                                "sender": inviter,
                                "body": f"You have been invited to a room by {inviter}. Say hello and introduce yourself.",
                                "room_id": invite_room_id,
                                "room_name": "",
                            },
                        )
                        await self._task_queue.put(task)
                        has_activity = True
                    else:
                        logger.warning(
                            f"Failed to join room {invite_room_id} for {cred.agent_id}"
                        )

                # --- Handle new messages ---
                if hb and hb.get("has_updates"):
                    rooms_with_unread = hb.get("rooms_with_unread", [])
                    enqueued = 0

                    for room_info in rooms_with_unread:
                        room_id = room_info.get("room_id", "")
                        if not room_id:
                            continue

                        # Fetch messages since last sync
                        messages = await client.get_messages(
                            api_key=cred.api_key,
                            room_id=room_id,
                            limit=10,
                            since=cred.sync_token if cred.sync_token else None,
                        )

                        if messages:
                            # Fetch room metadata (member_count + creator)
                            room_meta = await self._get_room_meta(
                                client, cred.api_key, room_id
                            )
                            is_dm = room_meta["member_count"] <= 2
                            is_creator = (
                                room_meta["creator"] is not None
                                and room_meta["creator"] == cred.matrix_user_id
                            )

                            for msg in messages:
                                # Skip own messages
                                if msg.get("sender") == cred.matrix_user_id:
                                    continue

                                # Dedup: skip already-processed events
                                event_id = msg.get("event_id", "")
                                if event_id and event_id in self._processed_event_ids:
                                    continue

                                # Mention filter for group rooms:
                                # - DM rooms: always process
                                # - Room creator: always process (always-active rule)
                                # - Others: only process if explicitly mentioned
                                if not is_dm and not is_creator and not self._is_mentioned(msg, cred):
                                    if event_id:
                                        self._processed_event_ids.add(event_id)
                                    continue

                                # Safety net: skip if rate limited
                                if self._check_room_rate_limit(cred.agent_id, room_id):
                                    continue

                                task = MessageTask(
                                    credential=cred,
                                    room_id=room_id,
                                    message_event={
                                        **msg,
                                        "room_id": room_id,
                                        "room_name": room_info.get("room_name", ""),
                                    },
                                )
                                await self._task_queue.put(task)
                                if event_id:
                                    self._processed_event_ids.add(event_id)
                                enqueued += 1

                        # Prune dedup cache if too large
                        if len(self._processed_event_ids) > self._max_event_id_cache:
                            # Keep only the most recent half
                            excess = len(self._processed_event_ids) - self._max_event_id_cache // 2
                            for _ in range(excess):
                                self._processed_event_ids.pop()

                    if enqueued > 0:
                        logger.info(
                            f"Enqueued {enqueued} message(s) for agent {cred.agent_id}"
                        )
                    has_activity = has_activity or enqueued > 0

                if has_activity:
                    # Adaptive: shorten interval for active agents
                    next_poll = now + timedelta(seconds=POLL_MIN_INTERVAL)
                else:
                    # Adaptive: lengthen interval for idle agents
                    current_interval = POLL_INITIAL
                    npt = cred.next_poll_time
                    if npt:
                        # Ensure timezone-aware for comparison
                        if npt.tzinfo is None:
                            npt = npt.replace(tzinfo=timezone.utc)
                    if npt and npt <= now:
                        # 用实际经过时间推算当前间隔，逐步递增
                        last_interval = (now - npt).total_seconds() + POLL_STEP_UP
                        current_interval = min(
                            max(last_interval, POLL_MIN_INTERVAL),
                            POLL_MAX_INTERVAL,
                        )
                    next_poll = now + timedelta(seconds=current_interval)
            except Exception as e:
                logger.warning(f"Error fetching messages for {cred.agent_id}: {e}")
                # 出错时使用默认间隔，避免快速重试

            # Update next poll time（即使消息获取失败也要更新，避免快速重试）
            await self.cred_mgr.update_next_poll_time(cred.agent_id, next_poll)

            # Update sync token if provided
            if hb and hb.get("next_batch"):
                await self.cred_mgr.update_sync_token(
                    cred.agent_id, hb["next_batch"]
                )

        finally:
            await client.close()

    # =========================================================================
    # Workers
    # =========================================================================

    async def _worker(self, worker_id: int) -> None:
        """Worker coroutine: process messages from the queue."""
        while True:
            try:
                task = await self._task_queue.get()
                try:
                    self._processing_agents.add(task.credential.agent_id)
                    await self._process_message(task, worker_id)
                finally:
                    self._processing_agents.discard(task.credential.agent_id)
                    self._task_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[Worker {worker_id}] Unexpected error: {e}")

    async def _process_message(self, task: MessageTask, worker_id: int) -> None:
        """
        Process a single Matrix message through AgentRuntime.

        Flow:
        1. Build execution prompt via MatrixContextBuilder
        2. Call AgentRuntime.run()
        3. Write result to Inbox
        4. Mark room as read
        """
        cred = task.credential
        event = task.message_event
        agent_id = cred.agent_id

        sender = event.get("sender", "unknown")
        body = event.get("body", "")[:100]
        logger.info(
            f"[Worker {worker_id}] Processing message for {agent_id}: "
            f"{sender} in {task.room_id} — {body}..."
        )

        try:
            # 1. Build prompt
            client = NexusMatrixClient(server_url=cred.server_url)
            try:
                builder = MatrixContextBuilder(
                    message_event=event,
                    credential=cred,
                    client=client,
                    agent_id=agent_id,
                )
                prompt = await builder.build_prompt(self.history_config)
            finally:
                await client.close()

            # 2. Create ChannelTag for this message
            channel_tag = ChannelTag.matrix(
                sender_name=event.get("sender_display_name", sender),
                sender_id=sender,
                room_id=task.room_id,
                room_name=event.get("room_name", ""),
            )

            # Prefix prompt with ChannelTag
            tagged_prompt = f"{channel_tag.format()}\n{prompt}"

            # 3. Call AgentRuntime
            from xyz_agent_context.agent_runtime import AgentRuntime

            runtime = AgentRuntime()
            final_output = []

            async for response in runtime.run(
                agent_id=agent_id,
                user_id=sender,  # Sender acts as the interaction target
                input_content=tagged_prompt,
                working_source=WorkingSource.MATRIX,
                trigger_extra_data={"channel_tag": channel_tag.to_dict()},
            ):
                if hasattr(response, "message_type"):
                    if response.message_type == MessageType.AGENT_RESPONSE:
                        if hasattr(response, "delta") and response.delta:
                            final_output.append(response.delta)

            content = "".join(final_output)

            # 4. Write to Inbox (agent replies via matrix_send_message tool, not forced here)
            await self._write_to_inbox(cred, event, content, room_id=task.room_id)

            # 5. Mark as read
            read_client = NexusMatrixClient(server_url=cred.server_url)
            try:
                await read_client.mark_read(
                    api_key=cred.api_key, room_id=task.room_id
                )
            finally:
                await read_client.close()

            logger.info(
                f"[Worker {worker_id}] Message processed for {agent_id}, "
                f"output length: {len(content)}"
            )

        except Exception as e:
            logger.error(
                f"[Worker {worker_id}] Failed to process message "
                f"for {agent_id}: {e}"
            )

    async def _write_to_inbox(
        self,
        cred: MatrixCredential,
        event: Dict[str, Any],
        agent_output: str,
        room_id: str = "",
    ) -> None:
        """Write Matrix conversation result to the Agent owner's Inbox.

        Stores rich source JSON with room_id and sender info so the agent inbox
        can group messages by room and resolve agent identities.
        """
        import json as _json

        try:
            sender = event.get("sender_display_name", event.get("sender", "Unknown"))
            sender_id = event.get("sender", "")
            room_name = event.get("room_name", "Matrix Room")
            actual_room_id = room_id or event.get("room_id", "")

            title = f"Matrix: {sender} in {room_name}"
            content = (
                f"**From**: {sender}\n"
                f"**Room**: {room_name}\n"
                f"**Message**: {event.get('body', '')}\n\n"
                f"---\n\n"
                f"**Your response**:\n{agent_output}"
            )

            msg_id = f"msg_{uuid4().hex[:16]}"

            # Look up the Agent's owner (creator)
            from xyz_agent_context.repository import AgentRepository
            agent_repo = AgentRepository(self.db)
            try:
                agent = await agent_repo.get_by_id(cred.agent_id)
                owner_user_id = agent.created_by if agent else ""
            except Exception as e:
                logger.warning(f"Failed to look up agent owner for {cred.agent_id}: {e}")
                owner_user_id = ""

            if not owner_user_id:
                logger.warning(
                    f"Cannot write to inbox: no owner found for agent {cred.agent_id}"
                )
                return

            # Build rich source JSON (bypasses MessageSource's type/id-only model)
            source_json = _json.dumps({
                "type": "matrix",
                "id": cred.agent_id,
                "room_id": actual_room_id,
                "room_name": room_name,
                "sender_id": sender_id,
                "sender_name": sender,
            }, ensure_ascii=False)

            from xyz_agent_context.utils import utc_now
            await self.db.insert("inbox_table", {
                "message_id": msg_id,
                "user_id": owner_user_id,
                "source": source_json,
                "event_id": event.get("event_id", "") or None,
                "message_type": InboxMessageType.CHANNEL_MESSAGE.value,
                "title": title,
                "content": content,
                "is_read": False,
                "created_at": utc_now(),
            })

        except Exception as e:
            logger.error(f"Failed to write Matrix message to inbox: {e}")


# =============================================================================
# Entry Points
# =============================================================================

def run_matrix_trigger(
    base_poll_interval: int = 10,
    max_workers: int = 5,
) -> None:
    """
    Run MatrixTrigger (called by ModuleRunner or standalone).

    Args:
        base_poll_interval: Base polling cycle interval in seconds
        max_workers: Max concurrent workers
    """
    import xyz_agent_context.settings  # noqa: F401 — ensure .env is loaded

    trigger = MatrixTrigger(
        base_poll_interval=base_poll_interval,
        max_workers=max_workers,
    )
    asyncio.run(trigger.start())


def main():
    """CLI entry point for MatrixTrigger."""
    parser = argparse.ArgumentParser(
        description="MatrixTrigger — Background Matrix Message Poller",
    )
    parser.add_argument(
        "--interval", "-i", type=int, default=10,
        help="Base poll interval in seconds (default: 10)",
    )
    parser.add_argument(
        "--workers", "-w", type=int, default=5,
        help="Max concurrent workers (default: 5)",
    )
    parser.add_argument(
        "--no-history", action="store_true",
        help="Disable conversation history loading in prompts",
    )
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("MatrixTrigger — Background Matrix Message Poller")
    logger.info(f"  Poll interval: {args.interval}s")
    logger.info(f"  Max workers: {args.workers}")
    logger.info(f"  History: {'disabled' if args.no_history else 'enabled'}")
    logger.info("=" * 60)
    logger.info("Press Ctrl+C to stop")

    history_config = ChannelHistoryConfig(
        load_conversation_history=not args.no_history,
    )

    trigger = MatrixTrigger(
        base_poll_interval=args.interval,
        max_workers=args.workers,
        history_config=history_config,
    )

    import xyz_agent_context.settings  # noqa: F401
    asyncio.run(trigger.start())


if __name__ == "__main__":
    main()
