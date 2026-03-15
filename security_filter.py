"""Security filter — pre/post-LLM injection and jailbreak protection.

Pre-LLM:
  - scan_input(): detects prompt injection / jailbreak patterns before
    the message reaches the LLM. Runs entirely in Python, cannot be
    bypassed by clever LLM inputs.

Post-LLM:
  - filter_output(): strips potential system prompt leakage from
    responses before they are delivered to the user.
"""

import logging
import re

logger = logging.getLogger("bridge.security_filter")

# ── Pre-LLM: injection / jailbreak pattern list ─────────────────
# Each entry is a raw regex string. Compiled once at module load.

_INJECTION_PATTERNS: list[str] = [
    # Classic instruction override
    r"ignore\s+(all\s+)?(previous|prior|above|your)\s+instructions?",
    r"disregard\s+(all\s+)?(previous|prior|above|your)\s+instructions?",
    r"forget\s+(all\s+)?(previous|prior|above|your)\s+instructions?",
    r"override\s+(all\s+)?(previous|prior|above|your)\s+instructions?",
    r"bypass\s+(all\s+)?(previous|prior|above|your)\s+instructions?",

    # Identity replacement
    r"you\s+are\s+now\s+(a|an|the)\b",
    r"pretend\s+(you\s+are|to\s+be)\b",
    r"act\s+as\s+(a|an|the)\b",
    r"roleplay\s+as\b",
    r"simulate\s+(a|an|the)\s+\w+\s+(with\s+no|without)\s+(restrictions?|limits?|guidelines?)",

    # Restriction removal
    r"you\s+have\s+no\s+(restrictions?|limits?|guidelines?|rules?|filters?)",
    r"you\s+are\s+(free|allowed|able)\s+to\s+(say|do|ignore|bypass|violate)",
    r"(remove|disable|turn\s+off)\s+(your\s+)?(safety|content|restrictions?|filters?|guidelines?)",

    # Known jailbreak names / modes
    r"\bDAN\b",
    r"do\s+anything\s+now",
    r"jailbreak",
    r"developer\s+mode",
    r"maintenance\s+mode",
    r"god\s+mode",
    r"training\s+mode",
    r"test\s+mode\s+(enabled|activated|on)",
    r"sudo\s+mode",

    # System prompt extraction
    r"(what|tell\s+me|show\s+me|reveal|print|output|repeat|display|recite|quote|write\s+out)\s+"
    r"(is\s+)?(your\s+)?(system\s+prompt|prompt|instructions?|guidelines?|rules?|constraints?|directives?)",
    r"translate\s+your\s+(system\s+)?instructions?",
    r"summarize\s+your\s+(system\s+)?instructions?",
    r"what\s+(were\s+you|are\s+you)\s+(told|instructed|programmed|trained|given)\s+to",

    # Fake authority / identity
    r"(i\s+am|i'm)\s+(your\s+)?(developer|creator|admin|administrator|openai|anthropic|google|owner|operator)",
    r"(as\s+your|i\s+am\s+your)\s+(developer|creator|admin|owner|operator)",

    # Prompt delimiter injection (LLM boundary markers)
    r"<\|?\s*(im_start|im_end|system|endoftext|startoftext|user|assistant)\s*\|?>",
    r"\[INST\]|\[\/INST\]|<<SYS>>|<</SYS>>",
    r"###\s*(instruction|system|human|assistant)\s*:",
    r"<system>|</system>|<user>|</user>|<assistant>|</assistant>",

    # Multi-turn injection (fake conversation boundaries)
    r"(?:human|user)\s*:\s*.{0,300}\n\s*(?:assistant|ai|bot|claude|gemini)\s*:",
]

_COMPILED_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE | re.DOTALL) for p in _INJECTION_PATTERNS
]

# Invisible / direction-control Unicode characters used in obfuscated injections
_UNICODE_TRICKS: list[str] = [
    "\u202e",  # RTL override
    "\u202d",  # LTR override
    "\u200b",  # zero-width space
    "\u200c",  # zero-width non-joiner
    "\u200d",  # zero-width joiner
    "\ufeff",  # BOM / zero-width no-break space
    "\u2060",  # word joiner
    "\u00ad",  # soft hyphen
    "\u034f",  # combining grapheme joiner
    "\u115f",  # hangul choseong filler
    "\u1160",  # hangul jungseong filler
    "\u3164",  # hangul filler
    "\uffa0",  # halfwidth hangul filler
]


def _strip_unicode_tricks(text: str) -> str:
    """Remove invisible/direction-override Unicode characters."""
    for ch in _UNICODE_TRICKS:
        text = text.replace(ch, "")
    return text


def scan_input(text: str, is_owner: bool = False) -> tuple[bool, str, str]:
    """Scan user input for prompt injection and jailbreak patterns.

    Args:
        text:     The raw user message.
        is_owner: True if the sender is the bot owner.
                  Owners bypass jailbreak checks (but still get Unicode cleaned).

    Returns:
        (blocked, reason, cleaned_text)
        - blocked:      True → reject the message, do not send to LLM.
        - reason:       Non-empty string explaining the block (send to user).
        - cleaned_text: Unicode-sanitized version for use if not blocked.
    """
    cleaned = _strip_unicode_tricks(text)

    if is_owner:
        return False, "", cleaned

    for pattern in _COMPILED_PATTERNS:
        if pattern.search(cleaned):
            logger.warning(
                "Injection attempt blocked | pattern=%s | text=%.80s",
                pattern.pattern[:60],
                text,
            )
            return True, "⛔ Message blocked: contains disallowed instructions.", cleaned

    return False, "", cleaned


# ── Post-LLM: output filtering ───────────────────────────────────
# Patterns that suggest the LLM is leaking its system prompt content.

_LEAK_PATTERNS: list[str] = [
    r"(?:my|the)\s+(?:system\s+)?(?:instructions?|prompt)\s+(?:say|state|tell me to|instruct me to|are)\s*[:\"]",
    r"i\s+(?:was|am|have been)\s+(?:instructed|told|programmed|trained|given instructions?)\s+to\b",
    r"(?:here\s+is|here\s+are|the following\s+(?:are|is))\s+my\s+(?:instructions?|system\s+prompt|guidelines?)",
    r"as\s+per\s+my\s+(?:instructions?|system\s+prompt|guidelines?|configuration)",
    r"(?:i\s+am|i'm)\s+configured\s+(?:to|with)",
    r"my\s+system\s+prompt\s+(?:says?|states?|includes?|contains?)",
]

_COMPILED_LEAK_PATTERNS: list[re.Pattern] = [
    re.compile(p, re.IGNORECASE) for p in _LEAK_PATTERNS
]

# Keyword clusters — high density suggests system prompt leakage
_SYSTEM_KEYWORDS: list[str] = [
    "system prompt",
    "you are a",
    "your role is",
    "your purpose is",
    "you must never",
    "you should always",
    "do not reveal",
    "keep confidential",
    "never share",
    "always respond",
    "you are configured",
]

_LEAK_KEYWORD_THRESHOLD = 3  # how many keywords before we flag


def filter_output(response: str) -> str:
    """Scan LLM response for system prompt leakage and sanitize.

    Replaces leaking sections with [REDACTED] and logs a warning.
    Returns the (possibly modified) response.
    """
    for pattern in _COMPILED_LEAK_PATTERNS:
        if pattern.search(response):
            logger.warning("System prompt leak detected in response — redacting")
            response = pattern.sub("[REDACTED]", response)

    lower = response.lower()
    keyword_hits = sum(1 for kw in _SYSTEM_KEYWORDS if kw in lower)
    if keyword_hits >= _LEAK_KEYWORD_THRESHOLD:
        logger.warning(
            "High system-prompt keyword density in response (%d/%d keywords)",
            keyword_hits,
            len(_SYSTEM_KEYWORDS),
        )
        # Log the warning; don't hard-block to avoid false positives on legitimate
        # responses that discuss AI behaviour. The pattern redaction above handles
        # explicit leaks.

    return response
