"""Ollama-based message router for multi-instance Claude.

Uses local qwen2.5:7b to determine if a user message explicitly references
a specific Claude instance. Only called when 2+ instances exist.
"""

import logging

import httpx

logger = logging.getLogger("bridge.router")

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
ROUTER_MODEL = "qwen2.5:7b-instruct"
ROUTER_TIMEOUT = 10.0  # seconds — keep it snappy


async def route_message(message: str, instances: list[dict]) -> int | None:
    """Determine if message explicitly references a specific instance.

    Args:
        message: The user's message text.
        instances: List of dicts with 'id' and 'title' keys.

    Returns:
        Instance ID if explicitly referenced, or None to use active instance.
    """
    if not instances or len(instances) < 2:
        return None

    instance_list = "\n".join(
        f"{inst['id']}. \"{inst['title']}\"" for inst in instances
    )

    prompt = (
        "You are a message router. Given a list of named AI assistant instances "
        "and a user message, determine if the user is EXPLICITLY referring to a "
        "specific instance by its number or title.\n\n"
        f"Instances:\n{instance_list}\n\n"
        f"User message: \"{message}\"\n\n"
        "Does the user explicitly reference a specific instance? "
        "If YES, respond with ONLY the instance number (e.g. '2'). "
        "If NO (the message is just a regular question/request), respond with ONLY 'none'.\n\n"
        "Answer:"
    )

    try:
        async with httpx.AsyncClient(timeout=ROUTER_TIMEOUT) as client:
            resp = await client.post(
                OLLAMA_URL,
                json={
                    "model": ROUTER_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.0, "num_predict": 10},
                },
            )
            resp.raise_for_status()
            result = resp.json().get("response", "").strip().lower()
            logger.info("Router response: %s", result)

            # Parse response
            if result == "none" or not result:
                return None
            # Extract first number from response
            for word in result.split():
                if word.isdigit():
                    instance_id = int(word)
                    # Validate it's a real instance
                    valid_ids = {inst["id"] for inst in instances}
                    if instance_id in valid_ids:
                        return instance_id
            return None

    except httpx.TimeoutException:
        logger.warning("Router timed out, using active instance")
        return None
    except Exception as e:
        logger.warning("Router error, using active instance: %s", e)
        return None
