"""
ProxyScrape API source.
"""

import aiohttp
from typing import List
from core.models import Proxy
from .base import BaseSource


class ProxyScrapeSouce(BaseSource):
    """Scrape proxies from ProxyScrape API v2."""

    name = "ProxyScrape"
    base_url = "https://api.proxyscrape.com/v2/"

    PROTOCOLS = {
        "http": {
            "url": "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000&country=all&ssl=all&anonymity=all",
            "protocol": "http",
        },
        "socks4": {
            "url": "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks4&timeout=10000&country=all",
            "protocol": "socks4",
        },
        "socks5": {
            "url": "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=socks5&timeout=10000&country=all",
            "protocol": "socks5",
        },
    }

    async def fetch(self) -> List[Proxy]:
        """Fetch proxies from all ProxyScrape protocol endpoints."""
        all_proxies = []

        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for proto_name, config in self.PROTOCOLS.items():
                try:
                    async with session.get(config["url"]) as resp:
                        if resp.status == 200:
                            text = await resp.text()
                            proxies = self.parse_many(
                                text,
                                protocol=config["protocol"],
                                source=f"ProxyScrape-{proto_name}",
                            )
                            all_proxies.extend(proxies)
                except Exception:
                    continue

        return all_proxies
