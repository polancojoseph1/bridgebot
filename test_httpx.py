import asyncio
import httpx
import httpcore
import socket
import ipaddress

class SafeNetworkBackend(httpcore.AsyncNetworkBackend):
    def __init__(self, original_backend: httpcore.AsyncNetworkBackend):
        self.original_backend = original_backend

    async def connect_tcp(self, host: str, port: int, timeout=None, local_address=None, **kwargs):
        print(f"Connecting to {host}:{port}")
        return await self.original_backend.connect_tcp(host, port, timeout=timeout, local_address=local_address, **kwargs)

    async def connect_unix_socket(self, server_hostname: str, path: str, timeout=None, **kwargs):
        return await self.original_backend.connect_unix_socket(server_hostname, path, timeout=timeout, **kwargs)

    async def sleep(self, seconds: float):
        return await self.original_backend.sleep(seconds)

async def main():
    transport = httpx.AsyncHTTPTransport()
    transport._pool._network_backend = SafeNetworkBackend(transport._pool._network_backend)

    async with httpx.AsyncClient(transport=transport) as client:
        try:
            r = await client.get("http://example.com")
            print(r.status_code)
        except Exception as e:
            print("Error", e)

asyncio.run(main())
