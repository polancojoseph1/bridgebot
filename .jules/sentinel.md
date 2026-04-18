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

## 2024-05-24 - Unsanitized Path Traversal in Catch-All Routes
**Vulnerability:** The `serve_bridge_cloud_ui` catch-all route `/{full_path:path}` served arbitrary files using `FileResponse` because the `full_path` string was concatenated with a base directory (`_BC_BUILD / full_path`) without verifying that the resulting path stayed within the intended directory boundaries.
**Learning:** FastAPI's catch-all `/{path:path}` parameter receives the raw requested URI (potentially URL-encoded) which can include `../` path traversal sequences. Using this input directly in `Path()` concatenation and `FileResponse` allows attackers to escape the intended directory and read sensitive server files.
**Prevention:** Always sanitize and enforce directory boundaries on user-provided file paths. Use `os.path.commonpath([os.path.realpath(target), os.path.realpath(base)]) == os.path.realpath(base)` to ensure the resolved file path strictly resides within the intended directory.

## 2024-05-28 - Overly Permissive CORS Configuration
**Vulnerability:** The FastAPI application used `allow_origins=["*"]` in the `CORSMiddleware` configuration, allowing any domain to make cross-origin requests to the API.
**Learning:** Using `["*"]` for CORS origins nullifies the security benefits of the Same-Origin Policy, allowing malicious websites to make unauthorized requests to the API on behalf of the user, potentially leading to data exfiltration or Cross-Site Request Forgery (CSRF).
**Prevention:** Always parse and explicitly whitelist allowed origins using environment variables (e.g., `CORS_ALLOW_ORIGINS`) and default to an empty list `[]` to ensure cross-origin requests are blocked by default unless explicitly configured.

## 2024-06-15 - DNS Rebinding in HTTPX Proxy Endpoints
**Vulnerability:** The SSRF protection in `v1_api.py` (`_is_safe_url`) resolved the hostname via `socket.gethostbyname` to check if the IP was private. However, `httpx` resolved the hostname again independently during the actual HTTP request, leading to a Time-of-Check to Time-of-Use (TOCTOU) vulnerability where an attacker could exploit DNS rebinding to proxy requests to internal IPs.
**Learning:** Checking a hostname's IP address asynchronously before passing the hostname to an HTTP client that performs its own DNS resolution does not prevent DNS rebinding attacks. The DNS TTL could expire or be maliciously configured to return a safe IP during validation and a private IP during the connection.
**Prevention:** Always pin the DNS resolution by supplying a custom `AsyncNetworkBackend` to `httpcore`/`httpx` that performs the IP validation internally. Pass the verified IP address directly to the underlying `connect_tcp` function while preserving the original hostname for SNI, ensuring the exact validated IP is connected to.
