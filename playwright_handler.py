"""Playwright browser automation handler for bridgebot.

Provides async screenshot and page-content extraction using Chromium (headless).
Used by /screenshot and /browse commands, and available for bots via shell.

Install: pip install playwright && playwright install chromium
"""

import asyncio
import logging
import tempfile
import os
import socket
import ipaddress
import time
import threading
from urllib.parse import urlparse

logger = logging.getLogger("bridge.playwright")

# Default viewport
VIEWPORT = {"width": 1280, "height": 900}
# Max chars returned from get_page_text
MAX_TEXT_CHARS = 8000
# Page load timeout ms
PAGE_TIMEOUT = 30000

# Thread-safe bounded DNS cache for SSRF protection
from collections import OrderedDict
class BoundedCache:
    def __init__(self, capacity=1000):
        self.cache = OrderedDict()
        self.capacity = capacity
        self.lock = threading.Lock()

    def get(self, key):
        with self.lock:
            if key not in self.cache:
                return None
            self.cache.move_to_end(key)
            return self.cache[key]

    def set(self, key, value):
        with self.lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            self.cache[key] = value
            if len(self.cache) > self.capacity:
                self.cache.popitem(last=False)

_dns_cache = BoundedCache(capacity=1000)
DNS_CACHE_TTL = 5.0
_dns_executor = None

async def _is_safe_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme == "data":
            return True
        if parsed.scheme not in ("http", "https"):
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        cached = _dns_cache.get(hostname)
        if cached and time.time() - cached['time'] < DNS_CACHE_TTL:
            return cached['safe']

        loop = asyncio.get_running_loop()
        global _dns_executor
        if _dns_executor is None:
            from concurrent.futures import ThreadPoolExecutor
            _dns_executor = ThreadPoolExecutor(max_workers=5)

        try:
            # We use a limited thread pool and asyncio.wait_for to prevent starvation and hanging DNS attacks
            addr_info = await asyncio.wait_for(
                loop.run_in_executor(
                    _dns_executor, socket.getaddrinfo, hostname, 80, socket.AF_UNSPEC, socket.SOCK_STREAM
                ), timeout=2.0
            )
        except (socket.gaierror, asyncio.TimeoutError):
            return False

        is_safe = True
        for family, type, proto, canonname, sockaddr in addr_info:
            ip = sockaddr[0]
            try:
                ip_obj = ipaddress.ip_address(ip)
                if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_multicast or ip_obj.is_unspecified or ip_obj.is_reserved:
                    is_safe = False
                    break
            except ValueError:
                is_safe = False
                break

        _dns_cache.set(hostname, {'safe': is_safe, 'time': time.time()})
        return is_safe
    except Exception:
        return False

async def _route_handler(route):
    if await _is_safe_url(route.request.url):
        # We can't perfectly prevent DNS rebinding in Chromium without a full proxy,
        # but intercepting requests and using a timeout/cache limits the window and filters most basic SSRF.
        await route.continue_()
    else:
        await route.abort("accessdenied")

async def screenshot(url: str, full_page: bool = False) -> str:
    """Navigate to url and take a screenshot. Returns path to PNG temp file."""
    from playwright.async_api import async_playwright

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png", prefix="pw_shot_")
    tmp.close()
    path = tmp.name
    os.chmod(path, 0o600)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page(viewport=VIEWPORT)
            await page.route("**/*", _route_handler)
            await page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
            # Brief pause for JS-rendered content
            await asyncio.sleep(1.5)
            await page.screenshot(path=path, full_page=full_page)
            logger.info("Screenshot saved: %s (%d bytes)", path, os.path.getsize(path))
        finally:
            await browser.close()

    return path


async def get_page_text(url: str) -> str:
    """Navigate to url and extract readable text content. Returns plain text."""
    from playwright.async_api import async_playwright

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            page = await browser.new_page(viewport=VIEWPORT)
            await page.route("**/*", _route_handler)
            await page.goto(url, wait_until="domcontentloaded", timeout=PAGE_TIMEOUT)
            await asyncio.sleep(1.0)
            title = await page.title()
            # Extract inner text (strips HTML, keeps structure)
            text = await page.evaluate("""() => {
                // Remove script/style nodes
                document.querySelectorAll('script,style,nav,footer,header,[aria-hidden="true"]')
                    .forEach(el => el.remove());
                return document.body ? document.body.innerText : '';
            }""")
        finally:
            await browser.close()

    # Clean up whitespace
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    clean = "\n".join(lines)
    if len(clean) > MAX_TEXT_CHARS:
        clean = clean[:MAX_TEXT_CHARS] + f"\n\n[...truncated at {MAX_TEXT_CHARS} chars]"
    return f"**{title}**\n\n{clean}" if title else clean


async def screenshot_and_text(url: str) -> tuple[str, str]:
    """Take screenshot AND extract text. Returns (png_path, text)."""
    png_path, text = await asyncio.gather(
        screenshot(url),
        get_page_text(url),
    )
    return png_path, text
