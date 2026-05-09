"""
GitHub proxy list sources — scrapes from multiple open-source proxy list repos.
"""

import aiohttp
import asyncio
from typing import List
from core.models import Proxy
from .base import BaseSource


class GithubListsSource(BaseSource):
    """Scrape proxies from multiple GitHub proxy list repositories."""

    name = "GitHub Lists"

    # Format: (url, protocol, source_label)
    SOURCES = [
        # TheSpeedX/PROXY-List
        (
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
            "http",
            "TheSpeedX-HTTP",
        ),
        (
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks4.txt",
            "socks4",
            "TheSpeedX-SOCKS4",
        ),
        (
            "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
            "socks5",
            "TheSpeedX-SOCKS5",
        ),
        # monosans/proxy-list
        (
            "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
            "http",
            "monosans-HTTP",
        ),
        (
            "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks4.txt",
            "socks4",
            "monosans-SOCKS4",
        ),
        (
            "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
            "socks5",
            "monosans-SOCKS5",
        ),
        # ShiftyTR/Proxy-List
        (
            "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/http.txt",
            "http",
            "ShiftyTR-HTTP",
        ),
        (
            "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/https.txt",
            "https",
            "ShiftyTR-HTTPS",
        ),
        (
            "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks4.txt",
            "socks4",
            "ShiftyTR-SOCKS4",
        ),
        (
            "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/socks5.txt",
            "socks5",
            "ShiftyTR-SOCKS5",
        ),
        # clarketm/proxy-list
        (
            "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
            "http",
            "clarketm",
        ),
        # hookzof/socks5_list
        (
            "https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt",
            "socks5",
            "hookzof-SOCKS5",
        ),
        # MuRongPIG/Proxy-Master
        (
            "https://raw.githubusercontent.com/MuRongPIG/Proxy-Master/main/http.txt",
            "http",
            "ProxyMaster-HTTP",
        ),
        (
            "https://raw.githubusercontent.com/MuRongPIG/Proxy-Master/main/socks4.txt",
            "socks4",
            "ProxyMaster-SOCKS4",
        ),
        (
            "https://raw.githubusercontent.com/MuRongPIG/Proxy-Master/main/socks5.txt",
            "socks5",
            "ProxyMaster-SOCKS5",
        ),
        # Zaeem20/FREE_PROXY_LIST
        (
            "https://raw.githubusercontent.com/Zaeem20/FREE_PROXY_LIST/master/http.txt",
            "http",
            "Zaeem20-HTTP",
        ),
        (
            "https://raw.githubusercontent.com/Zaeem20/FREE_PROXY_LIST/master/https.txt",
            "https",
            "Zaeem20-HTTPS",
        ),
        (
            "https://raw.githubusercontent.com/Zaeem20/FREE_PROXY_LIST/master/socks4.txt",
            "socks4",
            "Zaeem20-SOCKS4",
        ),
        (
            "https://raw.githubusercontent.com/Zaeem20/FREE_PROXY_LIST/master/socks5.txt",
            "socks5",
            "Zaeem20-SOCKS5",
        ),
        # roosterkid/openproxylist
        (
            "https://raw.githubusercontent.com/roosterkid/openproxylist/main/HTTPS_RAW.txt",
            "https",
            "roosterkid-HTTPS",
        ),
        (
            "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS4_RAW.txt",
            "socks4",
            "roosterkid-SOCKS4",
        ),
        (
            "https://raw.githubusercontent.com/roosterkid/openproxylist/main/SOCKS5_RAW.txt",
            "socks5",
            "roosterkid-SOCKS5",
        ),
    ]

    async def _fetch_one(self, session: aiohttp.ClientSession, url: str,
                         protocol: str, source_label: str) -> List[Proxy]:
        """Fetch proxies from a single GitHub raw URL."""
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    return self.parse_many(text, protocol=protocol, source=source_label)
        except Exception:
            pass
        return []

    async def fetch(self) -> List[Proxy]:
        """Fetch proxies from all GitHub sources concurrently."""
        all_proxies = []
        timeout = aiohttp.ClientTimeout(total=30)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            tasks = [
                self._fetch_one(session, url, proto, label)
                for url, proto, label in self.SOURCES
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, list):
                    all_proxies.extend(result)

        return all_proxies
