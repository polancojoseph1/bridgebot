import re

with open("v1_api.py", "r") as f:
    content = f.read()

# Let's extract the context manager
match = re.search(r"@contextlib\.asynccontextmanager.*?(?=\n# ──)", content, re.DOTALL)
if match:
    old_fn = match.group(0)
    new_fn = """@contextlib.asynccontextmanager
async def _get_safe_client(timeout: typing.Optional[float] = None, block_private_ips: bool = True) -> typing.AsyncGenerator[httpx.AsyncClient, None]:
    import httpx
    import httpcore
    from httpcore.backends.asyncio import AsyncIOBackend

    class SafeTransport(httpx.AsyncHTTPTransport):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # Recreate the pool with our custom backend, preserving other settings
            # from the initialized _pool
            pool_kwargs = {
                "ssl_context": self._pool._ssl_context,
                "max_connections": self._pool._max_connections,
                "max_keepalive_connections": self._pool._max_keepalive_connections,
                "keepalive_expiry": self._pool._keepalive_expiry,
                "http1": self._pool._http1,
                "http2": self._pool._http2,
                "retries": self._pool._retries,
                "local_address": self._pool._local_address,
                "uds": self._pool._uds,
                "network_backend": _SafeAnyIOBackend(AsyncIOBackend(), block_private_ips=block_private_ips),
            }
            self._pool = httpcore.AsyncConnectionPool(**pool_kwargs)

    transport = SafeTransport()
    async with httpx.AsyncClient(transport=transport, timeout=timeout) as client:
        yield client
"""
    content = content.replace(old_fn, new_fn)

with open("v1_api.py", "w") as f:
    f.write(content)
