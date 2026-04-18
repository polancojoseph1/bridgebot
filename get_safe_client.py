from httpcore import AnyIOBackend, AsyncNetworkBackend, AsyncNetworkStream
import typing
import socket
import ipaddress
import asyncio
import httpcore
import httpx

class SafeAnyIOBackend(AsyncNetworkBackend):
    def __init__(self, original_backend: AsyncNetworkBackend):
        self._original = original_backend

    async def connect_tcp(self, host: str, port: int, timeout: typing.Optional[float] = None, local_address: typing.Optional[str] = None, **kwargs) -> AsyncNetworkStream:
        loop = asyncio.get_running_loop()
        try:
            ip = await loop.run_in_executor(None, socket.gethostbyname, host)
        except socket.gaierror:
            raise httpcore.ConnectError("DNS resolution failed")

        ip_obj = ipaddress.ip_address(ip)
        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_multicast or ip_obj.is_unspecified or ip_obj.is_reserved:
            raise httpcore.ConnectError(f"Blocked SSRF attempt: {ip}")

        return await self._original.connect_tcp(
            ip, port, timeout=timeout, local_address=local_address, **kwargs
        )

    async def connect_tls(self, *args, **kwargs):
        return await self._original.connect_tls(*args, **kwargs)

    async def connect_unix_socket(self, *args, **kwargs):
        return await self._original.connect_unix_socket(*args, **kwargs)

def get_safe_client(timeout: typing.Optional[float] = None) -> httpx.AsyncClient:
    backend = SafeAnyIOBackend(AnyIOBackend())
    transport = httpx.AsyncHTTPTransport()
    transport._pool = httpcore.AsyncConnectionPool(network_backend=backend)
    return httpx.AsyncClient(transport=transport, timeout=timeout)
