"""Trigger worker — fires agents in response to events.

This module is purely event-driven (no polling loop).
fire() is called by:
  - The /triggers/webhook/<id> HTTP endpoint (external events)
  - The /trigger run <id> Telegram command (manual)

Public API:
    init(instance_manager, send_fn)  — call once at startup
    fire(trigger_id)                 — fire a trigger by ID, returns True on success
"""

import asyncio
import logging
import time

logger = logging.getLogger("bridge.trigger_worker")

_instance_manager = None
_send_fn = None


def init(instance_manager, send_fn) -> None:
    """Initialize the worker. Call once at server startup."""
    global _instance_manager, _send_fn
    _instance_manager = instance_manager
    _send_fn = send_fn
    logger.info("Trigger worker initialized")


async def fire(trigger_id: str) -> bool:
    """Fire a trigger by ID.

    Looks up the trigger and its agent, sends a start notification,
    then runs the agent task in the background.
    Returns True if the trigger was found and dispatched, False otherwise.
    """
    from trigger_registry import get_trigger, record_fired
    from agent_registry import resolve_agent

    if _instance_manager is None or _send_fn is None:
        logger.error("Trigger worker not initialized — call init() at startup")
        return False

    trigger = get_trigger(trigger_id)
    if not trigger:
        logger.warning("fire(): trigger '%s' not found", trigger_id)
        return False

    if not trigger.enabled:
        logger.info("fire(): trigger '%s' is disabled, skipping", trigger_id)
        return False

    agent = resolve_agent(trigger.agent_id)
    if not agent:
        logger.warning("fire(): trigger '%s' references missing agent '%s'", trigger_id, trigger.agent_id)
        return False

    task = trigger.task_override or agent.proactive_task or f"Perform your role as the {agent.name} agent."
    chat_id = trigger.chat_id

    record_fired(trigger_id)
    logger.info("Firing trigger '%s' → agent '%s' | task: %s", trigger_id, agent.id, task[:80])

    await _send_fn(
        chat_id,
        f"⚡ **{agent.name}** [TRIGGER: {trigger_id}] — starting\n_{task[:150]}_",
        format_markdown=True,
    )

    asyncio.ensure_future(_run_agent(trigger_id, agent.id, agent.name, task, chat_id))
    return True


async def _run_agent(trigger_id: str, agent_id: str, agent_name: str, task: str, chat_id: int) -> None:
    """Run the agent task and notify when done."""
    from agent_manager import assign_task

    started = time.time()
    try:
        await assign_task(agent_id, task, chat_id, _instance_manager, _send_fn)
        elapsed = round(time.time() - started)
        await _send_fn(
            chat_id,
            f"✅ **{agent_name}** [TRIGGER: {trigger_id}] finished in {elapsed}s.",
            format_markdown=True,
        )
    except Exception as e:
        elapsed = round(time.time() - started)
        logger.error("Trigger '%s' agent run failed: %s", trigger_id, e)
        await _send_fn(
            chat_id,
            f"❌ **{agent_name}** [TRIGGER: {trigger_id}] failed after {elapsed}s: {e}",
            format_markdown=True,
        )
