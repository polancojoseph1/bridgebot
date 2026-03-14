"""Free runner — rotates across multiple free-tier API providers.

Providers tried in order. On 429 rate limit, automatically rotates to
the next provider. Each provider uses the OpenAI-compatible API format.
Qwen Coder is a CLI-based provider that slots in automatically if installed.

Supported providers (all free tier):
  - Groq        (llama-3.3-70b, very fast, generous RPM)
  - Cerebras    (llama-3.3-70b, ultra-fast ~2000 t/s)
  - SambaNova   (llama-3.3-70b, very fast, 400 req/day)
  - Gemini Flash (google AI studio free tier, 1500 req/day)
  - OpenRouter   (aggregates free models, no key needed for some)
  - Together AI  (free credits on signup)
  - Mistral      (free tier on small models)
  - Cohere       (free tier on Command-R)
  - Hugging Face (free inference API, hundreds of models)
  - NVIDIA NIM   (free credits on hosted models)
  - Qwen Coder   (CLI-based, 1000 req/day via qwen.ai OAuth — auto-detected if installed)

Configure in .env:
  GROQ_API_KEY=...
  CEREBRAS_API_KEY=...
  SAMBANOVA_API_KEY=...
  GEMINI_API_KEY=...
  OPENROUTER_API_KEY=...
  TOGETHER_API_KEY=...
  MISTRAL_API_KEY=...
  COHERE_API_KEY=...
  HF_API_KEY=...
  NVIDIA_API_KEY=...
  # Qwen: no key needed — install with: npm install -g @qwen-code/qwen-code
  # then run `qwen` once to complete OAuth login
"""

import asyncio
import base64
import copy
import logging
import os
import shutil
import tempfile
import time
from dataclasses import dataclass, field
from typing import Callable, Awaitable, Any

import httpx

from runners.base import RunnerBase

logger = logging.getLogger("bridge.free")

# --- Provider definitions ---

@dataclass
class Provider:
    name: str
    base_url: str
    model: str
    api_key: str
    # Cooldown tracking — set when provider hits a rate limit
    _cooldown_until: float = field(default=0.0, repr=False)
    _cooldown_seconds: float = field(default=60.0, repr=False)

    def is_available(self) -> bool:
        return bool(self.api_key) and time.time() >= self._cooldown_until

    def mark_rate_limited(self):
        self._cooldown_until = time.time() + self._cooldown_seconds
        logger.info("[free] %s rate limited — cooling down for %ds", self.name, self._cooldown_seconds)

    def mark_success(self):
        # Reset cooldown on success
        self._cooldown_until = 0.0


@dataclass
class QwenCLIProvider:
    """Qwen Coder CLI provider — uses subprocess instead of HTTP API."""
    name: str = "Qwen Coder"
    # Longer cooldown: quota errors are daily limits, not temporary rate limits
    _cooldown_until: float = field(default=0.0, repr=False)
    _cooldown_seconds: float = field(default=3600.0, repr=False)

    def is_available(self) -> bool:
        return shutil.which("qwen") is not None and time.time() >= self._cooldown_until

    def is_configured(self) -> bool:
        return shutil.which("qwen") is not None

    def mark_rate_limited(self):
        self._cooldown_until = time.time() + self._cooldown_seconds
        logger.info("[free] %s quota hit — cooling down for %ds", self.name, self._cooldown_seconds)

    def mark_success(self):
        self._cooldown_until = 0.0


def _messages_to_prompt(messages: list[dict]) -> str:
    """Convert OpenAI-format message list to a flat text prompt for CLI tools."""
    parts = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        # Handle multipart content (e.g. image + text blocks)
        if isinstance(content, list):
            content = " ".join(
                block.get("text", "") for block in content if block.get("type") == "text"
            )
        if role == "system":
            parts.append(f"[Instructions: {content}]")
        elif role == "user":
            parts.append(f"User: {content}")
        elif role == "assistant":
            parts.append(f"Assistant: {content}")
    return "\n\n".join(parts)


def _build_providers() -> list[Provider | QwenCLIProvider]:
    """Build provider list from environment variables."""
    return [
        Provider(
            name="Groq",
            base_url="https://api.groq.com/openai/v1",
            model=os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
            api_key=os.environ.get("GROQ_API_KEY", ""),
        ),
        Provider(
            name="Cerebras",
            base_url="https://api.cerebras.ai/v1",
            model=os.environ.get("CEREBRAS_MODEL", "llama-3.3-70b"),
            api_key=os.environ.get("CEREBRAS_API_KEY", ""),
        ),
        Provider(
            name="SambaNova",
            base_url="https://api.sambanova.ai/v1",
            model=os.environ.get("SAMBANOVA_MODEL", "Meta-Llama-3.3-70B-Instruct"),
            api_key=os.environ.get("SAMBANOVA_API_KEY", ""),
        ),
        Provider(
            name="Gemini Flash",
            base_url="https://generativelanguage.googleapis.com/v1beta/openai",
            model=os.environ.get("GEMINI_FREE_MODEL", "gemini-2.0-flash"),
            api_key=os.environ.get("GEMINI_API_KEY", ""),
        ),
        Provider(
            name="OpenRouter",
            base_url="https://openrouter.ai/api/v1",
            model=os.environ.get("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free"),
            api_key=os.environ.get("OPENROUTER_API_KEY", ""),
        ),
        Provider(
            name="Together AI",
            base_url="https://api.together.xyz/v1",
            model=os.environ.get("TOGETHER_MODEL", "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"),
            api_key=os.environ.get("TOGETHER_API_KEY", ""),
        ),
        Provider(
            name="Mistral",
            base_url="https://api.mistral.ai/v1",
            model=os.environ.get("MISTRAL_MODEL", "mistral-small-latest"),
            api_key=os.environ.get("MISTRAL_API_KEY", ""),
        ),
        Provider(
            name="Cohere",
            base_url="https://api.cohere.com/compatibility/v1",
            model=os.environ.get("COHERE_MODEL", "command-r-plus"),
            api_key=os.environ.get("COHERE_API_KEY", ""),
        ),
        Provider(
            name="Hugging Face",
            base_url="https://api-inference.huggingface.co/v1",
            model=os.environ.get("HF_MODEL", "meta-llama/Llama-3.3-70B-Instruct"),
            api_key=os.environ.get("HF_API_KEY", ""),
        ),
        Provider(
            name="NVIDIA NIM",
            base_url="https://integrate.api.nvidia.com/v1",
            model=os.environ.get("NVIDIA_MODEL", "meta/llama-3.3-70b-instruct"),
            api_key=os.environ.get("NVIDIA_API_KEY", ""),
        ),
        # Qwen Coder — CLI-based, auto-detected if installed. No API key needed.
        QwenCLIProvider(),
    ]


class FreeRunner(RunnerBase):
    name = "free"
    cli_command = ""  # No CLI binary — uses direct HTTP API

    def __init__(self):
        self.providers = _build_providers()
        self.timeout = int(os.environ.get("CLI_TIMEOUT", "120"))

        # Validate and cache config at startup (bad values silently kill all providers otherwise)
        try:
            self.max_tokens = int(os.environ.get("FREE_MAX_TOKENS", "4096"))
            if self.max_tokens <= 0:
                raise ValueError("must be > 0")
        except ValueError as e:
            logger.error("[free] Bad FREE_MAX_TOKENS: %s — using 4096", e)
            self.max_tokens = 4096

        try:
            self.temperature = float(os.environ.get("FREE_TEMPERATURE", "0.7"))
            if not (0.0 <= self.temperature <= 2.0):
                raise ValueError("must be in [0.0, 2.0]")
        except ValueError as e:
            logger.error("[free] Bad FREE_TEMPERATURE: %s — using 0.7", e)
            self.temperature = 0.7

        # Persistent HTTP client — reused across all requests for connection pooling
        self.client = httpx.AsyncClient()

        available = [
            p.name for p in self.providers
            if (isinstance(p, QwenCLIProvider) and p.is_configured()) or
               (isinstance(p, Provider) and p.api_key)
        ]
        logger.info("[free] Loaded providers: %s", available or ["none — add API keys to .env"])

    # --- Runner interface ---

    def new_session(self, instance) -> None:
        instance.session_started = False
        instance.conversation_history = []

    async def stop(self, instance) -> bool:
        # HTTP calls can't be cancelled mid-flight cleanly
        # Just flag it — the next poll will see was_stopped
        instance.was_stopped = True
        return True

    async def kill_all(self) -> int:
        return 0  # No long-running processes

    def is_available(self) -> bool:
        for p in self.providers:
            if isinstance(p, QwenCLIProvider) and p.is_configured():
                return True
            if isinstance(p, Provider) and p.api_key:
                return True
        return False

    async def run_query(self, prompt: str, timeout: int = 120) -> str:
        """Stateless one-shot query — no session history."""
        return await self._call_with_rotation(
            messages=[{"role": "user", "content": prompt}],
            timeout=timeout,
        )

    async def run(
        self,
        message: str,
        instance,
        on_progress: Callable[[str], Awaitable[None]] | None = None,
        image_path: str | None = None,
        memory_context: str = "",
        on_subprocess_started: Callable[[int, str, str], None] | None = None,
        chat_id: int = 0,
    ) -> str:
        instance.was_stopped = False

        # Initialize conversation history on instance if not present
        if not hasattr(instance, "conversation_history"):
            instance.conversation_history = []

        # Build messages
        messages = []

        # System prompt with memory context
        system_parts = []
        if memory_context:
            system_parts.append(memory_context)
        system_prompt = os.environ.get("CLI_SYSTEM_PROMPT", "")
        if system_prompt:
            system_parts.append(system_prompt)
        if system_parts:
            messages.append({"role": "system", "content": "\n\n".join(system_parts)})

        # Prior conversation turns — deep copy to prevent mutation of stored history
        messages.extend(copy.deepcopy(instance.conversation_history))

        # Current user message
        user_content = message
        if image_path:
            # Validate path (prevent traversal) and size before encoding
            try:
                real_path = os.path.realpath(image_path)
                tmp_dir = tempfile.gettempdir()
                if not real_path.startswith(tmp_dir):
                    return "❌ Invalid image path."
                size = os.path.getsize(real_path)
                if size > 10 * 1024 * 1024:
                    return "❌ Image too large (max 10MB)."
                with open(real_path, "rb") as f:
                    img_b64 = base64.b64encode(f.read()).decode()
                ext = os.path.splitext(real_path)[1].lower().lstrip(".")
                mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
                        "gif": "image/gif", "webp": "image/webp"}.get(ext, "image/jpeg")
                user_content = [
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{img_b64}"}},
                    {"type": "text", "text": message or "What's in this image?"},
                ]
            except Exception as e:
                logger.warning("[free] Could not encode image: %s", e)
                return f"❌ Could not process image: {e}"

        messages.append({"role": "user", "content": user_content})

        result = await self._call_with_rotation(
            messages=messages, timeout=self.timeout, on_progress=on_progress
        )

        if instance.was_stopped:
            return "🛑 Stopped."

        if not result.startswith("❌"):
            # Trim BEFORE appending so we never exceed 40 messages (20 turns)
            if len(instance.conversation_history) >= 40:
                instance.conversation_history = instance.conversation_history[-38:]
            instance.conversation_history.append({"role": "user", "content": message})
            instance.conversation_history.append({"role": "assistant", "content": result})
            instance.session_started = True

        return result

    # --- Core rotation logic ---

    async def _call_with_rotation(
        self,
        messages: list[dict],
        timeout: int = 120,
        on_progress: Callable[[str], Awaitable[None]] | None = None,
    ) -> str:
        """Try each available provider in order. Rotate on 429 or error."""
        available = [p for p in self.providers if p.is_available()]

        if not available:
            configured = [
                p for p in self.providers
                if (isinstance(p, QwenCLIProvider) and p.is_configured()) or
                   (isinstance(p, Provider) and p.api_key)
            ]
            if configured:
                soonest = min(configured, key=lambda p: p._cooldown_until)
                wait = max(0, soonest._cooldown_until - time.time())
                return f"❌ All free providers are temporarily busy. Try again in {wait:.0f}s."
            return "❌ No providers configured. Add GROQ_API_KEY, GEMINI_API_KEY, etc. to your .env (or install Qwen: npm install -g @qwen-code/qwen-code)"

        last_error = ""
        deadline = time.time() + timeout  # Global timeout across all rotation attempts

        for provider in available:
            remaining = int(deadline - time.time())
            if remaining <= 5:
                return "❌ Timed out waiting for a free API response."

            if on_progress:
                await on_progress(f"🔄 Trying {provider.name}...")

            if isinstance(provider, QwenCLIProvider):
                logger.info("[free] Trying provider: %s (CLI)", provider.name)
            else:
                logger.info("[free] Trying provider: %s (%s)", provider.name, provider.model)

            try:
                if isinstance(provider, QwenCLIProvider):
                    response = await self._call_qwen_provider(provider, messages, remaining)
                else:
                    response = await self._call_provider(provider, messages, remaining)
                provider.mark_success()
                logger.info("[free] Success via %s", provider.name)
                return response

            except RateLimitError:
                provider.mark_rate_limited()
                logger.info("[free] Rotating away from %s", provider.name)
                continue

            except ProviderError as e:
                last_error = str(e)
                logger.warning("[free] %s error: %s", provider.name, e)
                # Short backoff on transient errors to avoid hammering the same provider
                if isinstance(provider, Provider):
                    provider._cooldown_until = time.time() + 15.0
                continue

            except Exception as e:
                last_error = str(e)
                logger.warning("[free] %s unexpected error: %s", provider.name, e)
                continue

        return f"❌ All providers failed. Last error: {last_error}"

    async def _call_provider(self, provider: Provider, messages: list[dict], timeout: int) -> str:
        """Make a single API call to a provider. Raises RateLimitError on 429."""
        headers = {
            "Authorization": f"Bearer {provider.api_key}",
            "Content-Type": "application/json",
        }
        # OpenRouter needs these for free tier
        if "openrouter" in provider.base_url:
            headers["HTTP-Referer"] = "https://bridgebot.local"
            headers["X-Title"] = "Bridgebot"

        payload = {
            "model": provider.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

        try:
            resp = await self.client.post(
                f"{provider.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=timeout,
            )
        except httpx.TimeoutException:
            raise ProviderError(f"{provider.name} timed out")
        except httpx.HTTPError as e:
            raise ProviderError(f"{provider.name} network error: {type(e).__name__}")

        if resp.status_code == 429:
            raise RateLimitError(f"{provider.name} rate limited")

        if resp.status_code != 200:
            raise ProviderError(f"{provider.name} returned {resp.status_code}")

        try:
            data = resp.json()
        except Exception:
            raise ProviderError(f"{provider.name} returned non-JSON response")

        choices = data.get("choices", [])
        if not choices:
            raise ProviderError(f"{provider.name} returned empty response")

        try:
            return choices[0]["message"]["content"].strip()
        except (KeyError, IndexError) as e:
            raise ProviderError(f"{provider.name} unexpected response format: {e}") from e


    async def _call_qwen_provider(self, provider: QwenCLIProvider, messages: list[dict], timeout: int) -> str:
        """Run the Qwen CLI as a provider slot. Converts messages to flat prompt text."""
        binary = shutil.which("qwen")
        if not binary:
            raise ProviderError("Qwen CLI not found in PATH")

        prompt = _messages_to_prompt(messages)
        cmd = [binary, "--yolo", "--output-format", "text", prompt]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.path.expanduser("~"),
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=float(timeout))
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                    await proc.wait()
                except ProcessLookupError:
                    pass
                raise ProviderError("Qwen CLI timed out")
        except OSError as e:
            raise ProviderError(f"Failed to start Qwen CLI: {e}")

        output = stdout.decode(errors="replace").strip()
        err = stderr.decode(errors="replace").strip()

        if proc.returncode != 0:
            err_lower = err.lower()
            # Match specific quota/rate patterns — avoid false positives on numeric strings
            if any(p in err_lower for p in ["quota exceeded", "rate limit", "too many requests", "daily limit"]):
                raise RateLimitError("Qwen quota reached")
            if any(p in err_lower for p in ["authentication", "unauthorized", "please login", "not logged in"]):
                raise ProviderError("Qwen needs re-authentication — open a terminal and run: qwen")
            raise ProviderError(f"Qwen CLI exited {proc.returncode}: {err[:200]}")

        if output:
            return output
        if err:
            raise ProviderError(f"Qwen returned no output. stderr: {err[:200]}")
        raise ProviderError("Qwen returned empty output")


# --- Custom exceptions ---

class RateLimitError(Exception):
    """Raised when a provider returns HTTP 429."""

class ProviderError(Exception):
    """Raised on any non-429 provider error."""
