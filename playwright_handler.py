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
import functools

logger = logging.getLogger("bridge.playwright")

# Simple LRU cache for DNS resolution results to prevent thread pool exhaustion DoS
from functools import lru_cache

@lru_cache(maxsize=1024)
def _resolve_and_check_sync(hostname: str) -> bool:
    try:
        addr_info = socket.getaddrinfo(hostname, 80, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for family, type, proto, canonname, sockaddr in addr_info:
            ip = sockaddr[0]
            try:
                ip_obj = ipaddress.ip_address(ip)
                if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_multicast or ip_obj.is_unspecified or ip_obj.is_reserved:
                    return False
            except ValueError:
                return False
        return True
    except socket.gaierror:
        return False

async def _is_safe_url(url_str: str) -> bool:
    try:
        parsed = urlparse(url_str)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False

        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(None, _resolve_and_check_sync, hostname)
        except Exception:
            return False
    except Exception:
        return False

async def route_handler(route):
    url = route.request.url
    if not await _is_safe_url(url):
        logger.warning(f"Blocked unsafe URL: {url}")
        await route.abort("accessdenied")
    else:
        await route.continue_()

# Default viewport
VIEWPORT = {"width": 1280, "height": 900}
# Max chars returned from get_page_text
MAX_TEXT_CHARS = 8000
# Page load timeout ms
PAGE_TIMEOUT = 30000


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
            await page.route("**/*", route_handler)
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
            await page.route("**/*", route_handler)
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
