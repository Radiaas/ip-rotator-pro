"""
IP Rotation Engine with multiple rotation strategies.
"""

import asyncio
import time
from typing import Optional
from datetime import datetime, timedelta
from core.models import Proxy, ProxyPool
from core.scraper import ProxyScraper
from core.validator import ProxyValidator
from utils.display import Display


class IPRotator:
    """
    Automatic IP rotation engine.
    Provides proxy rotation with auto-refresh and multiple strategies.
    """

    STRATEGIES = ["round_robin", "random", "smart", "fastest"]

    def __init__(self, pool: ProxyPool, scraper: ProxyScraper,
                 validator: ProxyValidator, display: Optional[Display] = None,
                 strategy: str = "smart", max_fail_count: int = 3,
                 auto_refresh_interval: int = 180):
        self.pool = pool
        self.scraper = scraper
        self.validator = validator
        self.display = display or Display()
        self.strategy = strategy
        self.max_fail_count = max_fail_count
        self.auto_refresh_interval = auto_refresh_interval  # Default 180s = 3 min
        self._request_count = 0
        self._last_refresh = None
        self._running = False
        self._refresh_task = None

    def get_proxy(self) -> Optional[Proxy]:
        """Get the next proxy based on the current rotation strategy."""
        strategy_map = {
            "round_robin": self.pool.get_next_round_robin,
            "random": self.pool.get_random,
            "smart": self.pool.get_smart,
            "fastest": self.pool.get_fastest,
        }

        getter = strategy_map.get(self.strategy, self.pool.get_smart)
        proxy = getter()

        if proxy:
            self._request_count += 1
            self.display.rotation_info(proxy, self._request_count)

        return proxy

    def report_failure(self, proxy: Proxy):
        """Report a proxy failure. Remove from pool if over max fails."""
        proxy.fail_count += 1
        proxy.last_checked = datetime.now()

        if proxy.fail_count >= self.max_fail_count:
            proxy.alive = False
            self.display.warning(
                f"Proxy {proxy.address} removed after {proxy.fail_count} failures"
            )

    def report_success(self, proxy: Proxy):
        """Report a proxy success."""
        proxy.success_count += 1
        proxy.last_checked = datetime.now()

    async def auto_refresh(self):
        """Background task that refreshes proxy pool every N seconds."""
        self._running = True
        self._last_refresh = datetime.now()

        self.display.auto_refresh_status(
            interval=self.auto_refresh_interval,
            next_refresh=(datetime.now() + timedelta(seconds=self.auto_refresh_interval)).strftime("%H:%M:%S"),
            pool_size=self.pool.size,
            alive=self.pool.alive_count,
        )

        while self._running:
            try:
                await asyncio.sleep(self.auto_refresh_interval)

                if not self._running:
                    break

                self.display.console.print()
                self.display.info(f"[~] Auto-refresh triggered at {datetime.now().strftime('%H:%M:%S')}")

                # Clear dead proxies
                removed = self.pool.remove_dead()
                if removed > 0:
                    self.display.info(f"Cleaned {removed} dead proxies")

                # Scrape fresh proxies
                await self.scraper.scrape_all()

                # Validate new proxies
                await self.validator.validate_all(remove_dead=True)

                self._last_refresh = datetime.now()
                next_refresh = (datetime.now() + timedelta(seconds=self.auto_refresh_interval)).strftime("%H:%M:%S")

                self.display.auto_refresh_status(
                    interval=self.auto_refresh_interval,
                    next_refresh=next_refresh,
                    pool_size=self.pool.size,
                    alive=self.pool.alive_count,
                )

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.display.error(f"Auto-refresh error: {e}")
                await asyncio.sleep(30)  # Wait before retrying

    def start_auto_refresh(self):
        """Start the auto-refresh background task."""
        if self._refresh_task is None or self._refresh_task.done():
            loop = asyncio.get_event_loop()
            self._refresh_task = loop.create_task(self.auto_refresh())
            self.display.success(
                f"Auto-refresh started (every {self.auto_refresh_interval}s / "
                f"{self.auto_refresh_interval // 60}min)"
            )

    def stop_auto_refresh(self):
        """Stop the auto-refresh background task."""
        self._running = False
        if self._refresh_task and not self._refresh_task.done():
            self._refresh_task.cancel()
            self.display.info("Auto-refresh stopped")

    async def initial_load(self):
        """Perform initial scrape + validate to populate pool."""
        self.display.section("Initial Pool Setup")

        # Scrape from all sources
        await self.scraper.scrape_all()

        # Validate all proxies
        if self.pool.size > 0:
            await self.validator.validate_all(remove_dead=True)

        alive = self.pool.alive_count
        if alive > 0:
            self.display.success(f"Pool ready with {alive} alive proxies")
        else:
            self.display.warning("No alive proxies found! Try increasing timeout or adding more sources.")

        # Show stats
        self.pool.update_stats()
        self.display.stats_panel(self.pool.stats)

        return alive
