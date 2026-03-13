"""FastAPI dependency for inbound peer authentication.

Peers authenticate by sending their shared token in the X-Collab-Token header.
This token was set when the peer was added — it is the token *they* send to
identify themselves on *our* instance.
"""

import logging

from fastapi import HTTPException, Request

from .config import get_peer_by_token

logger = logging.getLogger("bridge.collab.auth")


async def get_peer(request: Request) -> tuple[str, dict]:
    """FastAPI dependency: authenticate an inbound peer request.

    Reads X-Collab-Token from the request headers and looks up the matching
    peer entry in our registry.

    Returns:
        (peer_name, peer_dict) tuple.

    Raises:
        HTTPException 401 — no token provided.
        HTTPException 403 — token not recognised.
    """
    token = request.headers.get("X-Collab-Token", "").strip()
    if not token:
        logger.warning("Collab request from %s with no token", request.client)
        raise HTTPException(status_code=401, detail="X-Collab-Token header required")

    result = get_peer_by_token(token)
    if result is None:
        logger.warning("Collab request with unknown token from %s", request.client)
        raise HTTPException(status_code=403, detail="Unknown peer token")

    peer_name, peer_dict = result
    logger.debug("Authenticated peer '%s' from %s", peer_name, request.client)
    return (peer_name, peer_dict)
