import asyncio
from v1_api import _is_safe_url

async def main():
    print(await _is_safe_url("http://localhost"))
    print(await _is_safe_url("http://127.0.0.1"))
    print(await _is_safe_url("http://example.com"))

asyncio.run(main())
