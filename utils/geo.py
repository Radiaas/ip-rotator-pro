"""
GeoIP lookup utility using free APIs.
"""

import asyncio
import aiohttp
from typing import Tuple


class GeoIP:
    """Lookup country information from IP address."""

    # Cache to avoid repeated lookups
    _cache = {}

    @classmethod
    async def lookup(cls, ip: str, timeout: int = 5) -> Tuple[str, str]:
        """
        Lookup country for an IP address.
        Returns (country_name, country_code) tuple.
        """
        if ip in cls._cache:
            return cls._cache[ip]

        apis = [
            f"http://ip-api.com/json/{ip}?fields=country,countryCode",
        ]

        for api_url in apis:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(api_url, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                        if resp.status == 200:
                            data = await resp.json(content_type=None)
                            country = data.get("country", "Unknown")
                            code = data.get("countryCode", "??")
                            cls._cache[ip] = (country, code)
                            return country, code
            except Exception:
                continue

        cls._cache[ip] = ("Unknown", "??")
        return "Unknown", "??"

    @classmethod
    async def bulk_lookup(cls, ips: list, max_concurrent: int = 10) -> dict:
        """Lookup countries for multiple IPs concurrently."""
        semaphore = asyncio.Semaphore(max_concurrent)
        results = {}

        async def _lookup(ip):
            async with semaphore:
                country, code = await cls.lookup(ip)
                results[ip] = (country, code)
                # Rate limit for ip-api.com (45 requests/min for free)
                await asyncio.sleep(0.1)

        unique_ips = [ip for ip in set(ips) if ip not in cls._cache]
        if unique_ips:
            tasks = [_lookup(ip) for ip in unique_ips]
            await asyncio.gather(*tasks, return_exceptions=True)

        # Include cached results
        for ip in ips:
            if ip not in results and ip in cls._cache:
                results[ip] = cls._cache[ip]

        return results

    @classmethod
    def clear_cache(cls):
        """Clear the GeoIP cache."""
        cls._cache.clear()
