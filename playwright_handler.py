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
from urllib.parse import urlparse

logger = logging.getLogger("bridge.playwright")

# Default viewport
VIEWPORT = {"width": 1280, "height": 900}
# Max chars returned from get_page_text
MAX_TEXT_CHARS = 8000
# Page load timeout ms
PAGE_TIMEOUT = 30000




import time
import threading
_dns_cache = {}
_CACHE_TTL = 5.0  # seconds
_dns_cache_lock = threading.Lock()

def _resolve_and_check_ip_sync(hostname: str) -> bool:
    now = time.time()
    with _dns_cache_lock:
        if hostname in _dns_cache:
            cached_result, timestamp = _dns_cache[hostname]
            if now - timestamp < _CACHE_TTL:
                return cached_result

    try:
        addr_info = socket.getaddrinfo(hostname, 80, socket.AF_UNSPEC, socket.SOCK_STREAM)
    except socket.gaierror:
        with _dns_cache_lock:
            _dns_cache[hostname] = (False, now)
        return False

    for family, type, proto, canonname, sockaddr in addr_info:
        ip = sockaddr[0]
        try:
            ip_obj = ipaddress.ip_address(ip)
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_multicast or ip_obj.is_unspecified or ip_obj.is_reserved:
                with _dns_cache_lock:
                    _dns_cache[hostname] = (False, now)
                return False
        except ValueError:
            with _dns_cache_lock:
                _dns_cache[hostname] = (False, now)
            return False

    with _dns_cache_lock:
        _dns_cache[hostname] = (True, now)

        # Simple cache cleanup
        if len(_dns_cache) > 1000:
            keys_to_delete = [k for k, v in _dns_cache.items() if now - v[1] >= _CACHE_TTL]
            for k in keys_to_delete:
                del _dns_cache[k]

    return True


async def _route_interceptor(route):
    url = route.request.url
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https", "data"):
        await route.abort()
        return

    hostname = parsed.hostname
    if hostname:
        loop = asyncio.get_running_loop()
        is_safe = await loop.run_in_executor(None, _resolve_and_check_ip_sync, hostname)
        if not is_safe:
            await route.abort()
            return

    await route.continue_()

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
            await page.route("**/*", _route_interceptor)
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
            await page.route("**/*", _route_interceptor)
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
