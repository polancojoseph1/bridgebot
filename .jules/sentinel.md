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

## 2026-04-10 - [Security Improvement] Add rate limiting to proxy endpoints
**Vulnerability:** The API proxy endpoints (`/api/chat`, `/api/proxy`, `/api/proxy/verify`) in `v1_api.py` lacked rate limiting, making them susceptible to Denial of Service (DoS) attacks and abuse of external API connections.
**Learning:** All endpoints that perform significant processing or external network requests should be protected by rate limiting. Even endpoints meant to proxy requests to other services need rate limits to prevent abuse.
**Prevention:** Apply the `@_limiter.limit` decorator (e.g., `@_limiter.limit("30/minute")`) to all FastAPI endpoints, particularly those acting as proxies or making downstream requests.

## 2024-05-28 - Overly Permissive CORS Configuration
**Vulnerability:** The FastAPI application used `allow_origins=["*"]` in the `CORSMiddleware` configuration, allowing any domain to make cross-origin requests to the API.
**Learning:** Using `["*"]` for CORS origins nullifies the security benefits of the Same-Origin Policy, allowing malicious websites to make unauthorized requests to the API on behalf of the user, potentially leading to data exfiltration or Cross-Site Request Forgery (CSRF).
**Prevention:** Always parse and explicitly whitelist allowed origins using environment variables (e.g., `CORS_ALLOW_ORIGINS`) and default to an empty list `[]` to ensure cross-origin requests are blocked by default unless explicitly configured.

## 2026-04-14 - Missing Rate Limits on FastAPI Endpoints
**Vulnerability:** Several utility and health-check endpoints in `server.py` (e.g., `/health`, `/status`, `/wa/qr`, `/wa/status`, `/prompts`) were missing rate-limiting decorators, potentially exposing the server to denial-of-service (DoS) or enumeration attacks through excessive, unauthenticated requests.
**Learning:** The `slowapi` rate limiter decorator (`@_limiter.limit`) requires access to the client identifier, which it extracts from the `Request` object. Endpoints without a `request: Request` parameter in their function signature cannot be rate-limited using this standard middleware setup without causing a `TypeError` at runtime, leading to unprotected utility routes.
**Prevention:** When adding new FastAPI endpoints, always ensure the `request: Request` parameter is included in the function signature if rate-limiting might be required, and proactively apply the `@_limiter.limit` decorator to all public-facing or unauthenticated routes.
## 2024-05-28 - Overly Restrictive Rate Limits on Static Routes
**Vulnerability:** A lack of rate limiting on the SPA catch-all route (`/{full_path:path}`) exposed the application to potential DoS attacks. However, initially applying a standard API limit (e.g., `120/minute`) was flagged during review as a high risk for functional regression.
**Learning:** Modern Single Page Applications (SPAs) fetch dozens of static assets (JS, CSS, images, fonts) per page load. A low rate limit on routes serving static files can easily be triggered by normal user navigation, leading to false-positive 429 Too Many Requests errors and breaking the UI.
**Prevention:** When applying rate limits to catch-all UI endpoints serving static files, use a significantly higher threshold (e.g., `1200/minute`) to accommodate normal asset fetching while still mitigating severe brute-force or DoS attempts.
