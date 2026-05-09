"""
Multi-source proxy scraper engine.
"""

import asyncio
import time
from typing import List, Optional, Dict
from core.models import Proxy, ProxyPool
from sources.proxyscrape import ProxyScrapeSouce
from sources.github_lists import GithubListsSource
from sources.geonode import GeoNodeSource
from sources.web_scraper import WebScraperSource
from utils.display import Display


class ProxyScraper:
    """Scrape proxies from multiple sources concurrently."""

    SOURCE_CLASSES = {
        "proxyscrape": ProxyScrapeSouce,
        "github_lists": GithubListsSource,
        "geonode": GeoNodeSource,
        "web_scraper": WebScraperSource,
    }

    def __init__(self, pool: ProxyPool, display: Optional[Display] = None,
                 enabled_sources: Optional[List[str]] = None):
        self.pool = pool
        self.display = display or Display()
        self.enabled_sources = enabled_sources or list(self.SOURCE_CLASSES.keys())
        self.source_stats: Dict[str, Dict] = {}

    async def scrape_source(self, source_name: str) -> List[Proxy]:
        """Scrape proxies from a single source."""
        if source_name not in self.SOURCE_CLASSES:
            return []

        source_class = self.SOURCE_CLASSES[source_name]
        source = source_class()

        start = time.time()
        try:
            proxies = await source.fetch()
            elapsed = time.time() - start

            self.source_stats[source_name] = {
                "count": len(proxies),
                "elapsed": elapsed,
                "status": "success",
            }

            self.display.scrape_summary(source.name, len(proxies), elapsed)
            return proxies

        except Exception as e:
            elapsed = time.time() - start
            self.source_stats[source_name] = {
                "count": 0,
                "elapsed": elapsed,
                "status": f"error: {str(e)}",
            }
            self.display.scrape_summary(source.name, 0, elapsed)
            return []

    async def scrape_all(self, sources: Optional[List[str]] = None) -> int:
        """
        Scrape proxies from all enabled sources concurrently.
        Returns total number of unique proxies added to pool.
        """
        sources_to_scrape = sources or self.enabled_sources

        self.display.section("Scraping Proxies")
        self.display.info(f"Sources: {', '.join(sources_to_scrape)}")
        self.display.console.print()

        start = time.time()

        # Run all sources concurrently
        tasks = [self.scrape_source(src) for src in sources_to_scrape]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Add all proxies to pool (deduplication happens in pool.add_many)
        total_raw = 0
        all_proxies = []
        for result in results:
            if isinstance(result, list):
                total_raw += len(result)
                all_proxies.extend(result)

        added = self.pool.add_many(all_proxies)
        elapsed = time.time() - start

        self.display.console.print()
        self.display.separator()
        self.display.success(
            f"Scraping complete in {elapsed:.1f}s"
        )
        self.display.info(f"Raw proxies: {total_raw} | Unique added: {added} | Pool size: {self.pool.size}")

        return added

    async def scrape_single(self, source_name: str) -> int:
        """Scrape from a single source and add to pool."""
        self.display.section(f"Scraping from {source_name}")

        proxies = await self.scrape_source(source_name)
        added = self.pool.add_many(proxies)

        self.display.info(f"Added {added} unique proxies to pool")
        return added
