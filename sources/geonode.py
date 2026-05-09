"""
GeoNode API proxy source.
"""

import aiohttp
from typing import List
from core.models import Proxy
from .base import BaseSource


class GeoNodeSource(BaseSource):
    """Scrape proxies from GeoNode free proxy API."""

    name = "GeoNode"
    base_url = "https://proxylist.geonode.com/api/proxy-list"

    async def fetch(self) -> List[Proxy]:
        """Fetch proxies from GeoNode API with pagination."""
        all_proxies = []
        timeout = aiohttp.ClientTimeout(total=30)

        protocols_to_fetch = ["http", "https", "socks4", "socks5"]

        async with aiohttp.ClientSession(timeout=timeout) as session:
            for protocol in protocols_to_fetch:
                page = 1
                max_pages = 3  # Limit to avoid too many requests

                while page <= max_pages:
                    try:
                        params = {
                            "limit": 100,
                            "page": page,
                            "sort_by": "lastChecked",
                            "sort_type": "desc",
                            "protocols": protocol,
                        }

                        async with session.get(self.base_url, params=params) as resp:
                            if resp.status != 200:
                                break

                            data = await resp.json(content_type=None)
                            proxy_data = data.get("data", [])

                            if not proxy_data:
                                break

                            for item in proxy_data:
                                try:
                                    ip = item.get("ip", "")
                                    port = int(item.get("port", 0))

                                    if not ip or not port:
                                        continue

                                    # Get protocols from the proxy data
                                    proto_list = item.get("protocols", [protocol])
                                    proto = proto_list[0] if proto_list else protocol

                                    proxy = Proxy(
                                        ip=ip,
                                        port=port,
                                        protocol=proto.lower(),
                                        country=item.get("country", "Unknown"),
                                        country_code=item.get("countryCode", "??"),
                                        anonymity=item.get("anonymityLevel", "unknown").lower(),
                                        speed=float(item.get("responseTime", 0)),
                                        source=f"GeoNode-{proto.upper()}",
                                    )
                                    all_proxies.append(proxy)
                                except (ValueError, KeyError, IndexError):
                                    continue

                            # Check if there are more pages
                            total = data.get("total", 0)
                            if page * 100 >= total:
                                break

                            page += 1

                    except Exception:
                        break

        return all_proxies
