"""
Async proxy validator and speed tester.
"""

import asyncio
import aiohttp
import time
from datetime import datetime
from typing import List, Optional
from core.models import Proxy, ProxyPool
from utils.display import Display

try:
    from aiohttp_socks import ProxyConnector, ProxyType
    HAS_SOCKS = True
except ImportError:
    HAS_SOCKS = False


class ProxyValidator:
    """Validate proxies asynchronously with concurrent checking."""

    # Judge URLs to test proxy connectivity
    JUDGE_URLS = [
        "http://httpbin.org/ip",
        "http://api.ipify.org",
        "http://icanhazip.com",
        "http://ifconfig.me/ip",
        "http://checkip.amazonaws.com",
    ]

    def __init__(self, pool: ProxyPool, display: Optional[Display] = None,
                 timeout: int = 10, max_concurrent: int = 100,
                 retry_count: int = 2, judge_urls: Optional[List[str]] = None):
        self.pool = pool
        self.display = display or Display()
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.retry_count = retry_count
        self.judge_urls = judge_urls or self.JUDGE_URLS
        self._alive = 0
        self._dead = 0
        self._checked = 0

    async def _check_http_proxy(self, proxy: Proxy, session_timeout: aiohttp.ClientTimeout) -> bool:
        """Check if an HTTP/HTTPS proxy is alive."""
        proxy_url = f"http://{proxy.ip}:{proxy.port}"

        for judge_url in self.judge_urls[:2]:  # Try first 2 judges
            try:
                async with aiohttp.ClientSession(timeout=session_timeout) as session:
                    start = time.time()
                    async with session.get(
                        judge_url,
                        proxy=proxy_url,
                        ssl=False,
                    ) as resp:
                        if resp.status == 200:
                            elapsed = (time.time() - start) * 1000  # to ms
                            body = await resp.text()

                            # Verify we got a valid response (should contain an IP)
                            body = body.strip()
                            if body and (body.count(".") >= 3 or "origin" in body.lower()):
                                proxy.speed = elapsed
                                proxy.alive = True
                                proxy.success_count += 1
                                proxy.last_checked = datetime.now()

                                # Try to detect anonymity
                                if proxy.ip in body:
                                    proxy.anonymity = "transparent"
                                else:
                                    proxy.anonymity = "elite"

                                return True
            except Exception:
                continue

        return False

    async def _check_socks_proxy(self, proxy: Proxy) -> bool:
        """Check if a SOCKS4/SOCKS5 proxy is alive."""
        if not HAS_SOCKS:
            return False

        proxy_type_map = {
            "socks4": ProxyType.SOCKS4,
            "socks5": ProxyType.SOCKS5,
        }

        proxy_type = proxy_type_map.get(proxy.protocol)
        if not proxy_type:
            return False

        for judge_url in self.judge_urls[:2]:
            try:
                connector = ProxyConnector(
                    proxy_type=proxy_type,
                    host=proxy.ip,
                    port=proxy.port,
                )
                timeout = aiohttp.ClientTimeout(total=self.timeout)

                async with aiohttp.ClientSession(
                    connector=connector, timeout=timeout
                ) as session:
                    start = time.time()
                    async with session.get(judge_url) as resp:
                        if resp.status == 200:
                            elapsed = (time.time() - start) * 1000
                            body = await resp.text()

                            if body.strip():
                                proxy.speed = elapsed
                                proxy.alive = True
                                proxy.success_count += 1
                                proxy.last_checked = datetime.now()
                                proxy.anonymity = "elite"
                                return True
            except Exception:
                continue

        return False

    async def _validate_one(self, proxy: Proxy, semaphore: asyncio.Semaphore,
                            progress_callback=None) -> bool:
        """Validate a single proxy with retry logic."""
        async with semaphore:
            session_timeout = aiohttp.ClientTimeout(total=self.timeout)

            for attempt in range(self.retry_count):
                try:
                    if proxy.protocol in ("http", "https"):
                        result = await self._check_http_proxy(proxy, session_timeout)
                    elif proxy.protocol in ("socks4", "socks5"):
                        result = await self._check_socks_proxy(proxy)
                    else:
                        result = False

                    if result:
                        self._alive += 1
                        self._checked += 1
                        if progress_callback:
                            progress_callback()
                        return True

                except Exception:
                    if attempt < self.retry_count - 1:
                        await asyncio.sleep(0.5)
                    continue

            # Mark as dead after all retries
            proxy.alive = False
            proxy.fail_count += 1
            proxy.last_checked = datetime.now()
            self._dead += 1
            self._checked += 1
            if progress_callback:
                progress_callback()
            return False

    async def validate_all(self, proxies: Optional[List[Proxy]] = None,
                           remove_dead: bool = False) -> dict:
        """
        Validate all proxies in pool (or provided list) concurrently.
        Returns stats dict.
        """
        proxy_list = proxies or self.pool.proxies

        if not proxy_list:
            self.display.warning("No proxies to validate!")
            return {"alive": 0, "dead": 0, "total": 0}

        self.display.section("Validating Proxies")
        self.display.info(f"Checking {len(proxy_list)} proxies (timeout={self.timeout}s, concurrent={self.max_concurrent})")

        self._alive = 0
        self._dead = 0
        self._checked = 0

        semaphore = asyncio.Semaphore(self.max_concurrent)
        start = time.time()

        # Use rich progress bar
        progress = self.display.get_progress()
        with progress:
            task_id = progress.add_task("Validating...", total=len(proxy_list))

            def update_progress():
                progress.update(task_id, advance=1)

            tasks = [
                self._validate_one(proxy, semaphore, update_progress)
                for proxy in proxy_list
            ]
            await asyncio.gather(*tasks, return_exceptions=True)

        elapsed = time.time() - start

        # Update pool stats
        self.pool.update_stats()

        # Remove dead proxies if requested
        removed = 0
        if remove_dead:
            removed = self.pool.remove_dead()
            self.display.info(f"Removed {removed} dead proxies from pool")

        # Sort by speed
        self.pool.sort_by_speed()

        self.display.validation_result(self._alive, self._dead, elapsed)

        return {
            "alive": self._alive,
            "dead": self._dead,
            "total": len(proxy_list),
            "elapsed": elapsed,
            "removed": removed,
        }

    async def quick_check(self, proxy: Proxy) -> bool:
        """Quick check a single proxy (no retries, fast timeout)."""
        session_timeout = aiohttp.ClientTimeout(total=5)
        semaphore = asyncio.Semaphore(1)

        try:
            if proxy.protocol in ("http", "https"):
                return await self._check_http_proxy(proxy, session_timeout)
            elif proxy.protocol in ("socks4", "socks5"):
                return await self._check_socks_proxy(proxy)
        except Exception:
            return False

        return False
