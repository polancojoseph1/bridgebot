import asyncio
import httpcore
import httpx
import ipaddress
import socket

class SSRFNetworkBackend(httpcore.AsyncNetworkBackend):
    def __init__(self, original_backend: httpcore.AsyncNetworkBackend):
        self.original_backend = original_backend

    async def connect_tcp(self, host: str, port: int, timeout=None, local_address=None, **kwargs):
        loop = asyncio.get_running_loop()
        try:
            ip = await loop.run_in_executor(None, socket.gethostbyname, host)
        except socket.gaierror:
            raise httpcore.ConnectError(f"DNS resolution failed for {host}")

        ip_obj = ipaddress.ip_address(ip)
        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_multicast or ip_obj.is_unspecified or ip_obj.is_reserved:
            raise httpcore.ConnectError(f"SSRF Protection: Blocked connection to restricted IP {ip}")

        return await self.original_backend.connect_tcp(ip, port, timeout=timeout, local_address=local_address, **kwargs)

    async def connect_unix_socket(self, server_hostname: str, path: str, timeout=None, **kwargs):
        return await self.original_backend.connect_unix_socket(server_hostname, path, timeout=timeout, **kwargs)

    async def sleep(self, seconds: float):
        return await self.original_backend.sleep(seconds)

def create_safe_client(**kwargs) -> httpx.AsyncClient:
    transport = httpx.AsyncHTTPTransport()
    transport._pool._network_backend = SSRFNetworkBackend(transport._pool._network_backend)
    kwargs['transport'] = transport
    return httpx.AsyncClient(**kwargs)
