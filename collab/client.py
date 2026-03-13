"""HTTP client for calling peer collab endpoints.

Outbound calls always send X-Collab-Token: {peer["token"]} — this is the token
WE send to authenticate ourselves to the peer's instance.
"""

import logging

import httpx

logger = logging.getLogger("bridge.collab.client")

_DELEGATE_TIMEOUT = 60.0  # tasks can take a while
_BORROW_MESSAGE_TIMEOUT = 120.0  # borrow messages can be slow
_DEFAULT_TIMEOUT = 10.0
_BORROW_TIMEOUT = 15.0


def _headers(peer: dict) -> dict[str, str]:
    """Build auth headers for an outbound request to this peer."""
    return {"X-Collab-Token": peer.get("token", "")}


async def fetch_profile(peer: dict) -> dict | None:
    """GET /collab/profile — public, no auth required.

    Returns the peer's profile dict or None on failure.
    """
    url = peer.get("url", "").rstrip("/") + "/collab/profile"
    try:
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.debug("fetch_profile failed for %s: %s", url, e)
        return None


async def delegate_task(
    peer: dict,
    task: str,
    agent_id: str | None = None,
    bot: str | None = None,
    context: str = "",
) -> str:
    """POST /collab/delegate — ask the peer to run a task.

    Returns the result string or an error message.
    """
    url = peer.get("url", "").rstrip("/") + "/collab/delegate"
    payload: dict = {"task": task, "context": context}
    if agent_id:
        payload["agent_id"] = agent_id
    if bot:
        payload["bot"] = bot

    try:
        async with httpx.AsyncClient(timeout=_DELEGATE_TIMEOUT) as client:
            resp = await client.post(url, json=payload, headers=_headers(peer))
            resp.raise_for_status()
            data = resp.json()
            return data.get("result", "")
    except httpx.HTTPStatusError as e:
        logger.error("delegate_task HTTP %s from %s: %s", e.response.status_code, url, e)
        return f"Error from peer: HTTP {e.response.status_code}"
    except Exception as e:
        logger.error("delegate_task failed for %s: %s", url, e)
        return f"Error reaching peer: {e}"


async def search_peer_memory(peer: dict, query: str) -> list[dict]:
    """GET /collab/memory/search — search the peer's memory.

    Returns a list of result dicts or empty list on failure.
    """
    url = peer.get("url", "").rstrip("/") + "/collab/memory/search"
    try:
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
            resp = await client.get(url, params={"q": query}, headers=_headers(peer))
            resp.raise_for_status()
            data = resp.json()
            return data.get("results", [])
    except Exception as e:
        logger.debug("search_peer_memory failed for %s: %s", url, e)
        return []


async def fetch_peer_feed(peer: dict) -> list[dict]:
    """GET /collab/feed — get the peer's activity feed.

    Returns a list of event dicts or empty list on failure.
    """
    url = peer.get("url", "").rstrip("/") + "/collab/feed"
    try:
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
            resp = await client.get(url, headers=_headers(peer))
            resp.raise_for_status()
            data = resp.json()
            return data.get("events", [])
    except Exception as e:
        logger.debug("fetch_peer_feed failed for %s: %s", url, e)
        return []


async def broadcast_to_peer(peer: dict, message: str, from_name: str) -> bool:
    """POST /collab/broadcast — send a broadcast message to the peer.

    Returns True if the peer acknowledged it, False otherwise.
    """
    url = peer.get("url", "").rstrip("/") + "/collab/broadcast"
    payload = {"message": message, "from_name": from_name}
    try:
        async with httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT) as client:
            resp = await client.post(url, json=payload, headers=_headers(peer))
            resp.raise_for_status()
            return True
    except Exception as e:
        logger.debug("broadcast_to_peer failed for %s: %s", url, e)
        return False


async def borrow_start(peer: dict, bot: str | None = None) -> dict | None:
    """POST /collab/borrow/start — start a borrow session on a peer's instance.

    Returns {session_id, bot, label} or None on failure.
    """
    url = peer.get("url", "").rstrip("/") + "/collab/borrow/start"
    payload: dict = {}
    if bot:
        payload["bot"] = bot
    try:
        async with httpx.AsyncClient(timeout=_BORROW_TIMEOUT) as client:
            resp = await client.post(url, json=payload, headers=_headers(peer))
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as e:
        logger.error("borrow_start HTTP %s from %s: %s", e.response.status_code, url, e)
        return None
    except Exception as e:
        logger.error("borrow_start failed for %s: %s", url, e)
        return None


async def borrow_message(peer: dict, session_id: str, text: str) -> str:
    """POST /collab/borrow/message — send a message through an active borrow session.

    Returns the response string or an error message.
    """
    url = peer.get("url", "").rstrip("/") + "/collab/borrow/message"
    payload = {"session_id": session_id, "text": text}
    try:
        async with httpx.AsyncClient(timeout=_BORROW_MESSAGE_TIMEOUT) as client:
            resp = await client.post(url, json=payload, headers=_headers(peer))
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "")
    except httpx.HTTPStatusError as e:
        logger.error("borrow_message HTTP %s from %s: %s", e.response.status_code, url, e)
        return f"Error from peer: HTTP {e.response.status_code}"
    except Exception as e:
        logger.error("borrow_message failed for %s: %s", url, e)
        return f"Error reaching peer: {e}"


async def borrow_end(peer: dict, session_id: str) -> bool:
    """DELETE /collab/borrow/{session_id} — end a borrow session.

    Returns True on success, False on failure.
    """
    url = peer.get("url", "").rstrip("/") + f"/collab/borrow/{session_id}"
    try:
        async with httpx.AsyncClient(timeout=_BORROW_TIMEOUT) as client:
            resp = await client.delete(url, headers=_headers(peer))
            resp.raise_for_status()
            return True
    except httpx.HTTPStatusError as e:
        logger.error("borrow_end HTTP %s from %s: %s", e.response.status_code, url, e)
        return False
    except Exception as e:
        logger.error("borrow_end failed for %s: %s", url, e)
        return False
