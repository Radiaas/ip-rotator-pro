"""
Multi-format proxy exporter.
"""

import csv
import json
import os
from typing import List, Optional
from datetime import datetime
from core.models import Proxy


class Exporter:
    """Export proxies to various formats."""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def _get_filename(self, fmt: str, prefix: str = "proxies") -> str:
        """Generate timestamped filename."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(self.output_dir, f"{prefix}_{timestamp}.{fmt}")

    def to_txt(self, proxies: List[Proxy], filename: Optional[str] = None,
               include_protocol: bool = False) -> str:
        """Export proxies to TXT (IP:PORT format)."""
        if not filename:
            filename = self._get_filename("txt")

        with open(filename, "w", encoding="utf-8") as f:
            for proxy in proxies:
                if include_protocol:
                    f.write(f"{proxy.protocol}://{proxy.ip}:{proxy.port}\n")
                else:
                    f.write(f"{proxy.ip}:{proxy.port}\n")

        return filename

    def to_csv(self, proxies: List[Proxy], filename: Optional[str] = None) -> str:
        """Export proxies to CSV with full details."""
        if not filename:
            filename = self._get_filename("csv")

        fieldnames = [
            "ip", "port", "protocol", "country", "country_code",
            "anonymity", "speed_ms", "alive", "reliability",
            "last_checked", "source"
        ]

        with open(filename, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for proxy in proxies:
                writer.writerow(proxy.to_dict())

        return filename

    def to_json(self, proxies: List[Proxy], filename: Optional[str] = None) -> str:
        """Export proxies to JSON with full details."""
        if not filename:
            filename = self._get_filename("json")

        data = {
            "exported_at": datetime.now().isoformat(),
            "total": len(proxies),
            "alive": sum(1 for p in proxies if p.alive),
            "proxies": [proxy.to_dict() for proxy in proxies]
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return filename

    def export(self, proxies: List[Proxy], fmt: str = "txt",
               filename: Optional[str] = None, **kwargs) -> str:
        """Export proxies to specified format."""
        exporters = {
            "txt": self.to_txt,
            "csv": self.to_csv,
            "json": self.to_json,
        }

        exporter = exporters.get(fmt.lower())
        if not exporter:
            raise ValueError(f"Unsupported format: {fmt}. Use: {', '.join(exporters.keys())}")

        return exporter(proxies, filename=filename, **kwargs)

    def quick_save(self, proxies: List[Proxy]) -> str:
        """Quick save alive proxies to default txt file."""
        alive = [p for p in proxies if p.alive]
        filename = os.path.join(self.output_dir, "alive_proxies.txt")
        with open(filename, "w", encoding="utf-8") as f:
            for proxy in alive:
                f.write(f"{proxy.protocol}://{proxy.ip}:{proxy.port}\n")
        return filename
