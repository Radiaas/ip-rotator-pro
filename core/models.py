"""
Data models for IP Rotator Pro.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict
import threading
import random


@dataclass
class Proxy:
    """Represents a single proxy server."""
    ip: str
    port: int
    protocol: str = "http"            # http, https, socks4, socks5
    country: str = "Unknown"
    country_code: str = "??"
    anonymity: str = "unknown"        # transparent, anonymous, elite
    speed: float = 0.0                # response time in milliseconds
    last_checked: Optional[datetime] = None
    alive: bool = False
    fail_count: int = 0
    success_count: int = 0
    source: str = "unknown"

    @property
    def address(self) -> str:
        return f"{self.ip}:{self.port}"

    @property
    def url(self) -> str:
        return f"{self.protocol}://{self.ip}:{self.port}"

    @property
    def reliability(self) -> float:
        total = self.success_count + self.fail_count
        if total == 0:
            return 0.0
        return (self.success_count / total) * 100

    @property
    def speed_rating(self) -> str:
        if self.speed == 0:
            return "untested"
        elif self.speed < 1000:
            return "fast"
        elif self.speed < 3000:
            return "medium"
        elif self.speed < 7000:
            return "slow"
        else:
            return "very_slow"

    def to_dict(self) -> Dict:
        return {
            "ip": self.ip,
            "port": self.port,
            "protocol": self.protocol,
            "country": self.country,
            "country_code": self.country_code,
            "anonymity": self.anonymity,
            "speed_ms": round(self.speed, 2),
            "alive": self.alive,
            "reliability": round(self.reliability, 2),
            "last_checked": self.last_checked.isoformat() if self.last_checked else None,
            "source": self.source,
        }

    def __hash__(self):
        return hash((self.ip, self.port))

    def __eq__(self, other):
        if isinstance(other, Proxy):
            return self.ip == other.ip and self.port == other.port
        return False

    def __repr__(self):
        status = "+" if self.alive else "x"
        return f"Proxy({status} {self.protocol}://{self.ip}:{self.port} [{self.country_code}] {self.speed:.0f}ms)"


class ProxyPool:
    """Thread-safe pool of proxies with rotation support."""

    def __init__(self):
        self._proxies: List[Proxy] = []
        self._lock = threading.Lock()
        self._index = 0
        self._stats = {
            "total_scraped": 0,
            "total_alive": 0,
            "total_dead": 0,
            "sources": {},
            "countries": {},
            "protocols": {},
        }

    @property
    def proxies(self) -> List[Proxy]:
        with self._lock:
            return list(self._proxies)

    @property
    def alive_proxies(self) -> List[Proxy]:
        with self._lock:
            return [p for p in self._proxies if p.alive]

    @property
    def dead_proxies(self) -> List[Proxy]:
        with self._lock:
            return [p for p in self._proxies if not p.alive]

    @property
    def size(self) -> int:
        with self._lock:
            return len(self._proxies)

    @property
    def alive_count(self) -> int:
        with self._lock:
            return sum(1 for p in self._proxies if p.alive)

    @property
    def stats(self) -> Dict:
        return self._stats

    def add(self, proxy: Proxy) -> bool:
        """Add a proxy to the pool. Returns False if duplicate."""
        with self._lock:
            if proxy not in self._proxies:
                self._proxies.append(proxy)
                self._stats["total_scraped"] += 1
                # Track source
                src = proxy.source
                self._stats["sources"][src] = self._stats["sources"].get(src, 0) + 1
                return True
            return False

    def add_many(self, proxies: List[Proxy]) -> int:
        """Add multiple proxies, returns count of newly added."""
        added = 0
        for proxy in proxies:
            if self.add(proxy):
                added += 1
        return added

    def remove_dead(self) -> int:
        """Remove all dead proxies from pool."""
        with self._lock:
            before = len(self._proxies)
            self._proxies = [p for p in self._proxies if p.alive]
            removed = before - len(self._proxies)
            self._stats["total_dead"] += removed
            return removed

    def get_next_round_robin(self) -> Optional[Proxy]:
        """Get next alive proxy in round-robin order."""
        alive = self.alive_proxies
        if not alive:
            return None
        with self._lock:
            self._index = self._index % len(alive)
            proxy = alive[self._index]
            self._index += 1
            return proxy

    def get_random(self) -> Optional[Proxy]:
        """Get a random alive proxy."""
        alive = self.alive_proxies
        if not alive:
            return None
        return random.choice(alive)

    def get_fastest(self) -> Optional[Proxy]:
        """Get the fastest alive proxy."""
        alive = self.alive_proxies
        if not alive:
            return None
        return min(alive, key=lambda p: p.speed if p.speed > 0 else float("inf"))

    def get_smart(self) -> Optional[Proxy]:
        """Get proxy based on weighted score (speed + reliability)."""
        alive = self.alive_proxies
        if not alive:
            return None

        def score(p: Proxy) -> float:
            speed_score = max(0, 10000 - p.speed) / 10000 if p.speed > 0 else 0.5
            reliability_score = p.reliability / 100 if p.reliability > 0 else 0.5
            return speed_score * 0.6 + reliability_score * 0.4

        scored = sorted(alive, key=score, reverse=True)
        # Weighted random from top 30%
        top_n = max(1, len(scored) // 3)
        weights = list(range(top_n, 0, -1))
        return random.choices(scored[:top_n], weights=weights, k=1)[0]

    def update_stats(self):
        """Recalculate statistics."""
        with self._lock:
            self._stats["total_alive"] = sum(1 for p in self._proxies if p.alive)
            self._stats["total_dead"] = sum(1 for p in self._proxies if not p.alive)

            self._stats["countries"] = {}
            self._stats["protocols"] = {}
            for p in self._proxies:
                if p.alive:
                    cc = p.country_code
                    self._stats["countries"][cc] = self._stats["countries"].get(cc, 0) + 1
                    proto = p.protocol
                    self._stats["protocols"][proto] = self._stats["protocols"].get(proto, 0) + 1

    def sort_by_speed(self):
        """Sort proxies by speed (fastest first)."""
        with self._lock:
            self._proxies.sort(key=lambda p: p.speed if p.speed > 0 else float("inf"))

    def filter_by_country(self, country_code: str) -> List[Proxy]:
        """Get proxies filtered by country code."""
        with self._lock:
            return [p for p in self._proxies if p.country_code.upper() == country_code.upper() and p.alive]

    def filter_by_protocol(self, protocol: str) -> List[Proxy]:
        """Get proxies filtered by protocol."""
        with self._lock:
            return [p for p in self._proxies if p.protocol.lower() == protocol.lower() and p.alive]

    def filter_by_anonymity(self, anonymity: str) -> List[Proxy]:
        """Get proxies filtered by anonymity level."""
        with self._lock:
            return [p for p in self._proxies if p.anonymity.lower() == anonymity.lower() and p.alive]

    def clear(self):
        """Clear all proxies from pool."""
        with self._lock:
            self._proxies.clear()
            self._index = 0
