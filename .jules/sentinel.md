## 2024-03-27 - Unvalidated Proxy URLs
**Vulnerability:** The proxy endpoints in `v1_api.py` (`api_chat_proxy` and `api_proxy_verify`) accepted external URLs without validating the protocol scheme, creating an SSRF (Server-Side Request Forgery) risk where an attacker could pass a `file://` or `ftp://` scheme and exploit `httpx`.
**Learning:** Even internal routing/proxy endpoints should validate URLs explicitly (ensuring they only accept `http` and `https`), as libraries like `httpx` will throw unhandled exceptions or potentially perform arbitrary local requests if given `file://` protocols.
**Prevention:** Always parse and explicitly whitelist allowed protocols for any externally-provided or configuration-derived URLs before making HTTP requests.

## 2024-03-27 - Unbounded File Upload Memory Exhaustion (DoS)
**Vulnerability:** The `v1_upload` endpoint read the entire uploaded file into memory at once using `await file.read()`, causing a potential Denial of Service (DoS) attack if large files were uploaded.
**Learning:** Using `await file.read()` on `UploadFile` objects without chunking loads the full file content into system RAM, risking memory exhaustion crashes under load or malicious large payloads.
**Prevention:** Always process file uploads by reading in bounded chunks (e.g., `await file.read(1024 * 1024)`) and enforcing explicit size limits to prevent server resource exhaustion.
