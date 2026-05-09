"""
HTML web scraper source for proxy sites.
"""

import aiohttp
from typing import List
from core.models import Proxy
from .base import BaseSource

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


class WebScraperSource(BaseSource):
    """Scrape proxies from HTML-based proxy listing websites."""

    name = "Web Scraper"

    # Additional plain-text API sources that provide proxies
    PLAIN_TEXT_SOURCES = [
        # pubproxy.com free API
        ("https://www.proxy-list.download/api/v1/get?type=http", "http", "proxy-list-download-HTTP"),
        ("https://www.proxy-list.download/api/v1/get?type=https", "https", "proxy-list-download-HTTPS"),
        ("https://www.proxy-list.download/api/v1/get?type=socks4", "socks4", "proxy-list-download-SOCKS4"),
        ("https://www.proxy-list.download/api/v1/get?type=socks5", "socks5", "proxy-list-download-SOCKS5"),
        # Additional free APIs
        ("https://sunny9577.github.io/proxy-scraper/proxies.txt", "http", "sunny9577"),
        ("https://multiproxy.org/txt_all/proxy.txt", "http", "multiproxy"),
        ("https://raw.githubusercontent.com/prxchk/proxy-list/main/http.txt", "http", "prxchk-HTTP"),
        ("https://raw.githubusercontent.com/prxchk/proxy-list/main/socks4.txt", "socks4", "prxchk-SOCKS4"),
        ("https://raw.githubusercontent.com/prxchk/proxy-list/main/socks5.txt", "socks5", "prxchk-SOCKS5"),
    ]

    async def _fetch_plain_text(self, session: aiohttp.ClientSession,
                                 url: str, protocol: str, source: str) -> List[Proxy]:
        """Fetch proxies from a plain text source."""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    return self.parse_many(text, protocol=protocol, source=source)
        except Exception:
            pass
        return []

    async def _scrape_free_proxy_list(self, session: aiohttp.ClientSession) -> List[Proxy]:
        """Scrape proxies from free-proxy-list.net using BeautifulSoup."""
        if not HAS_BS4:
            return []

        proxies = []
        url = "https://free-proxy-list.net/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        try:
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    return []

                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")

                # Find the textarea with proxy list
                textarea = soup.find("textarea", class_="form-control")
                if textarea and textarea.text:
                    lines = textarea.text.strip().split("\n")
                    for line in lines:
                        proxy = self.parse_ip_port(line, protocol="http", source="FreeProxyList")
                        if proxy:
                            proxies.append(proxy)

                # Fallback: try parsing the table
                if not proxies:
                    table = soup.find("table", class_="table")
                    if table:
                        rows = table.find_all("tr")[1:]  # Skip header
                        for row in rows:
                            cols = row.find_all("td")
                            if len(cols) >= 7:
                                try:
                                    ip = cols[0].text.strip()
                                    port = int(cols[1].text.strip())
                                    country_code = cols[2].text.strip()
                                    anonymity = cols[4].text.strip().lower()
                                    is_https = cols[6].text.strip().lower() == "yes"

                                    proxy = Proxy(
                                        ip=ip,
                                        port=port,
                                        protocol="https" if is_https else "http",
                                        country_code=country_code,
                                        anonymity=anonymity if anonymity in ["elite proxy", "anonymous", "transparent"] else "unknown",
                                        source="FreeProxyList",
                                    )
                                    # Normalize anonymity
                                    if proxy.anonymity == "elite proxy":
                                        proxy.anonymity = "elite"
                                    proxies.append(proxy)
                                except (ValueError, IndexError):
                                    continue
        except Exception:
            pass

        return proxies

    async def fetch(self) -> List[Proxy]:
        """Fetch proxies from all web scraper sources."""
        all_proxies = []
        timeout = aiohttp.ClientTimeout(total=30)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            # Fetch plain text sources
            import asyncio
            tasks = [
                self._fetch_plain_text(session, url, proto, src)
                for url, proto, src in self.PLAIN_TEXT_SOURCES
            ]

            # Also scrape HTML sources
            tasks.append(self._scrape_free_proxy_list(session))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, list):
                    all_proxies.extend(result)

        return all_proxies
