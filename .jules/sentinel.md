## 2024-04-02 - Protect Webhook Endpoints from Timing Attacks
**Vulnerability:** The Telegram and WhatsApp webhook endpoints compared incoming secret strings with expected secrets using standard equality operators (`!=`).
**Learning:** Standard string equality (`!=` or `==`) comparisons stop at the first differing byte, allowing an attacker to determine the secret character by character by measuring the exact time taken to reject the request. This exposes the entire secret over many iterative requests (timing attack).
**Prevention:** Always use `secrets.compare_digest` for validating authentication tokens, API keys, and webhook secrets. This guarantees a constant-time comparison regardless of how many characters match, mitigating timing-based side-channel attacks.

## 2024-03-27 - Unvalidated Proxy URLs
**Vulnerability:** The proxy endpoints in `v1_api.py` (`api_chat_proxy` and `api_proxy_verify`) accepted external URLs without validating the protocol scheme, creating an SSRF (Server-Side Request Forgery) risk where an attacker could pass a `file://` or `ftp://` scheme and exploit `httpx`.
**Learning:** Even internal routing/proxy endpoints should validate URLs explicitly (ensuring they only accept `http` and `https`), as libraries like `httpx` will throw unhandled exceptions or potentially perform arbitrary local requests if given `file://` protocols.
**Prevention:** Always parse and explicitly whitelist allowed protocols for any externally-provided or configuration-derived URLs before making HTTP requests.

## 2024-03-27 - Unbounded File Upload Memory Exhaustion (DoS)
**Vulnerability:** The `v1_upload` endpoint read the entire uploaded file into memory at once using `await file.read()`, causing a potential Denial of Service (DoS) attack if large files were uploaded.
**Learning:** Using `await file.read()` on `UploadFile` objects without chunking loads the full file content into system RAM, risking memory exhaustion crashes under load or malicious large payloads.
**Prevention:** Always process file uploads by reading in bounded chunks (e.g., `await file.read(1024 * 1024)`) and enforcing explicit size limits to prevent server resource exhaustion.

## 2024-03-29 - Information Leakage in API Endpoints (CWE-209)
**Vulnerability:** Several API endpoints in `v1_api.py` (like `/v1/chat`, `/api/proxy`, `/api/proxy/verify`) were catching `Exception` and returning the raw stringified exception `str(exc)` directly to the client.
**Learning:** Exposing raw exception messages via API responses can leak sensitive internal information to attackers, including stack traces, file paths, library versions, and configuration details, aiding them in formulating further attacks.
**Prevention:** Always catch exceptions, log the full traceback server-side using `logger.error(..., exc_info=True)`, and return generic error messages (e.g., `"Internal Server Error"`) to external clients.

## 2024-05-20 - SSRF Prevention in API Proxy Endpoints
**Vulnerability:** The API endpoints (`api_chat_proxy`, `api_proxy`, `api_proxy_verify`) relied only on checking the URL scheme (`http`/`https`) via `urllib.parse.urlparse`, which fails to prevent Server-Side Request Forgery (SSRF) against internal or private IP ranges (e.g., `localhost`, `127.0.0.1`, `169.254.x.x`).
**Learning:** Checking only the scheme of a URL is not sufficient to prevent SSRF if the endpoint proxy logic fetches data from a target server dynamically determined by user input.
**Prevention:** Always validate and block local, private, and reserved IP addresses natively using `socket.gethostbyname()` and `ipaddress.ip_address` when validating external URL calls dynamically proxied by user input.
## 2026-03-23 - Prevent Path Traversal in FastAPI SPA Routes
**Vulnerability:** The SPA catch-all route (`/{full_path:path}`) in `server.py` constructed file paths by directly appending user input (`full_path`) to the base directory (`_BC_BUILD`) using `pathlib` without sanitizing for directory traversal sequences (like `../`).
**Learning:** Using `candidate = _BC_BUILD / full_path` is insufficient for security because if `full_path` is something like `../../etc/passwd`, the resulting path can resolve to locations outside the intended serving directory, enabling arbitrary file read vulnerabilities.
**Prevention:** To prevent Path Traversal vulnerabilities when serving files dynamically, always strictly enforce directory boundaries. Resolve both the base directory and the requested file path using `os.path.realpath`, and verify that `os.path.commonpath([resolved_candidate, resolved_base]) == resolved_base` before serving the file with `FileResponse`.
