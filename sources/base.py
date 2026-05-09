"""
Base source class for proxy sources.
"""

from abc import ABC, abstractmethod
from typing import List
from core.models import Proxy


class BaseSource(ABC):
    """Abstract base class for all proxy sources."""

    name: str = "base"
    url: str = ""

    @abstractmethod
    async def fetch(self) -> List[Proxy]:
        """Fetch proxies from this source. Must be implemented by subclasses."""
        pass

    def parse_ip_port(self, line: str, protocol: str = "http", source: str = None) -> Proxy:
        """Parse an IP:PORT line into a Proxy object."""
        line = line.strip()
        if not line or ":" not in line:
            return None

        try:
            parts = line.split(":")
            ip = parts[0].strip()
            port = int(parts[1].strip())

            # Basic IP validation
            octets = ip.split(".")
            if len(octets) != 4:
                return None
            for octet in octets:
                num = int(octet)
                if num < 0 or num > 255:
                    return None

            if port < 1 or port > 65535:
                return None

            return Proxy(
                ip=ip,
                port=port,
                protocol=protocol,
                source=source or self.name,
            )
        except (ValueError, IndexError):
            return None

    def parse_many(self, text: str, protocol: str = "http", source: str = None) -> List[Proxy]:
        """Parse multiple IP:PORT lines from text."""
        proxies = []
        for line in text.strip().splitlines():
            proxy = self.parse_ip_port(line, protocol, source)
            if proxy:
                proxies.append(proxy)
        return proxies
