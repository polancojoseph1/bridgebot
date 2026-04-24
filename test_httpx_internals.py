import httpx
transport = httpx.AsyncHTTPTransport()
print(hasattr(transport, '_pool'))
print(hasattr(transport._pool, '_network_backend'))
