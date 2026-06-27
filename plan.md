1.  **Add `import socket` and `import ipaddress` to `v1_api.py` module level.**
    *   The recent changes use `socket` and `ipaddress` inside `_is_safe_url`, but they are imported only locally inside `connect_tcp` of `SafeNetworkBackend`, leading to potential `NameError`s when `_is_safe_url` is called.
    *   To fix this and satisfy the sentinel instructions to enforce SSRF correctly, I'll add the imports at the top of the file, then modify `_is_safe_url` to be correct.
2.  **Fix `_is_safe_url` in `v1_api.py` to correctly check IP addresses using `socket.getaddrinfo`.**
    *   Currently, the code iterates over IPs but doesn't actually fail when all IPs are safe.
    *   It also claims `⚡ Bolt Optimization: Removed slow DNS pre-flight checks here since SafeNetworkBackend enforces them natively at the connection layer.` but leaves the `getaddrinfo` in.
    *   Actually, the memory says: `To prevent unhandled protocol exceptions when proxying requests with httpx (e.g., in v1_api.py), explicitly validate that the URL scheme is strictly 'http' or 'https'. While connection-level IP validation is the primary defense against DNS rebinding SSRF, pre-flight IP checks (using socket.getaddrinfo) must be maintained as defense-in-depth to provide clean 400 Bad Request errors instead of 500 Internal Server Errors.`
    *   The memory also says: `The pre-flight _is_safe_url URL validation in v1_api.py was using socket.gethostbyname, which only returns a single IPv4 address. This allows an attacker to bypass the check by providing a hostname that resolves to multiple IPs or an IPv6 address that resolves to local/private... Always use socket.getaddrinfo for IP validation and iterate through *all* returned IP addresses. Reject the request if *any* of the resolved IPs are private, loopback, link-local, multicast, unspecified, or reserved.`
    *   I will make sure `_is_safe_url` iterates through all IPs from `getaddrinfo` and rejects if ANY is private/local.
3.  **Run full test suite (`PYTHONPATH=. python3 -m pytest tests/`).**
    *   Ensure everything still passes.
4.  **Complete pre-commit steps.**
    *   Call `pre_commit_instructions` to ensure proper testing, verification, review, and reflection are done.
5.  **Submit PR.**
    *   Submit a PR with title format `🛡️ Sentinel: [MEDIUM] Fix SSRF in Pre-flight checks`.
