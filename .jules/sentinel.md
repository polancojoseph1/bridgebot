## 2024-04-02 - Protect Webhook Endpoints from Timing Attacks
**Vulnerability:** The Telegram and WhatsApp webhook endpoints compared incoming secret strings with expected secrets using standard equality operators (`!=`).
**Learning:** Standard string equality (`!=` or `==`) comparisons stop at the first differing byte, allowing an attacker to determine the secret character by character by measuring the exact time taken to reject the request. This exposes the entire secret over many iterative requests (timing attack).
**Prevention:** Always use `secrets.compare_digest` for validating authentication tokens, API keys, and webhook secrets. This guarantees a constant-time comparison regardless of how many characters match, mitigating timing-based side-channel attacks.
