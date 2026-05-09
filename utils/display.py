"""
Rich CLI display and dashboard for IP Rotator Pro.
"""

import os
import sys

# Fix Windows encoding
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.live import Live
from rich import box
from typing import List, Dict, Optional
import time

console = Console(force_terminal=True, color_system="auto")

BANNER = r"""
[bold cyan]
  ___  ____    ____        _        _
 |_ _||  _ \  |  _ \  ___ | |_  __ _| |_  ___  _ __
  | | | |_) | | |_) |/ _ \| __|/ _` | __|/ _ \| '__|
  | | |  __/  |  _ <| (_) | |_| (_| | |_| (_) | |
 |___||_|     |_| \_\\___/ \__|\__,_|\__|\___/|_|
[/bold cyan]
[dim]=====================================================[/dim]
[bold white]  [*] IP Rotator Pro v1.0 -- Proxy Scraper & Rotator[/bold white]
[dim]  github.com/your-username/ip-rotator-pro[/dim]
[dim]=====================================================[/dim]
"""


class Display:
    """Rich terminal display for IP Rotator Pro."""

    def __init__(self):
        self.console = console

    def banner(self):
        """Display the app banner."""
        self.console.print(BANNER)

    def info(self, msg: str):
        self.console.print(f"  [bold cyan][i][/bold cyan]  {msg}")

    def success(self, msg: str):
        self.console.print(f"  [bold green][OK][/bold green] {msg}")

    def warning(self, msg: str):
        self.console.print(f"  [bold yellow][!!][/bold yellow]  {msg}")

    def error(self, msg: str):
        self.console.print(f"  [bold red][X][/bold red] {msg}")

    def separator(self):
        self.console.print("[dim]  -------------------------------------------------[/dim]")

    def section(self, title: str):
        self.console.print(f"\n  [bold magenta]> {title}[/bold magenta]")
        self.separator()

    def proxy_table(self, proxies: list, title: str = "Proxy List", max_rows: int = 50):
        """Display proxies in a rich table."""
        table = Table(
            title=f"  {title}",
            box=box.ROUNDED,
            border_style="cyan",
            title_style="bold white",
            show_lines=False,
            padding=(0, 1),
        )

        table.add_column("#", style="dim", width=5, justify="right")
        table.add_column("IP Address", style="white", width=18)
        table.add_column("Port", style="cyan", width=7, justify="center")
        table.add_column("Protocol", style="magenta", width=10, justify="center")
        table.add_column("Country", width=8, justify="center")
        table.add_column("Anonymity", width=12, justify="center")
        table.add_column("Speed", width=10, justify="right")
        table.add_column("Status", width=8, justify="center")
        table.add_column("Reliability", width=12, justify="center")

        for i, proxy in enumerate(proxies[:max_rows], 1):
            # Status coloring
            if proxy.alive:
                status = "[bold green]ALIVE[/bold green]"
            else:
                status = "[bold red]DEAD[/bold red]"

            # Speed coloring
            if proxy.speed == 0:
                speed_str = "[dim]N/A[/dim]"
            elif proxy.speed < 1000:
                speed_str = f"[green]{proxy.speed:.0f}ms[/green]"
            elif proxy.speed < 3000:
                speed_str = f"[yellow]{proxy.speed:.0f}ms[/yellow]"
            else:
                speed_str = f"[red]{proxy.speed:.0f}ms[/red]"

            # Anonymity coloring
            anon = proxy.anonymity
            if anon == "elite":
                anon_str = f"[bold green]{anon}[/bold green]"
            elif anon == "anonymous":
                anon_str = f"[cyan]{anon}[/cyan]"
            elif anon == "transparent":
                anon_str = f"[yellow]{anon}[/yellow]"
            else:
                anon_str = f"[dim]{anon}[/dim]"

            # Reliability bar
            rel = proxy.reliability
            if rel >= 80:
                rel_str = f"[green]{rel:.0f}%[/green]"
            elif rel >= 50:
                rel_str = f"[yellow]{rel:.0f}%[/yellow]"
            elif rel > 0:
                rel_str = f"[red]{rel:.0f}%[/red]"
            else:
                rel_str = "[dim]N/A[/dim]"

            # Country flag emoji (simple mapping)
            country = f"{proxy.country_code}"

            table.add_row(
                str(i),
                proxy.ip,
                str(proxy.port),
                proxy.protocol.upper(),
                country,
                anon_str,
                speed_str,
                status,
                rel_str,
            )

        if len(proxies) > max_rows:
            table.add_row("", f"[dim]... and {len(proxies) - max_rows} more[/dim]", "", "", "", "", "", "", "")

        self.console.print()
        self.console.print(table)

    def stats_panel(self, stats: Dict):
        """Display statistics panel."""
        total = stats.get("total_scraped", 0)
        alive = stats.get("total_alive", 0)
        dead = stats.get("total_dead", 0)
        sources = stats.get("sources", {})
        countries = stats.get("countries", {})
        protocols = stats.get("protocols", {})

        # Main stats
        stats_text = Text()
        stats_text.append(f"  [#] Total Scraped:  ", style="dim")
        stats_text.append(f"{total}\n", style="bold white")
        stats_text.append(f"  [+] Alive:          ", style="dim")
        stats_text.append(f"{alive}\n", style="bold green")
        stats_text.append(f"  [-] Dead:           ", style="dim")
        stats_text.append(f"{dead}\n", style="bold red")

        if alive + dead > 0:
            rate = (alive / (alive + dead)) * 100
            stats_text.append(f"  [%] Success Rate:   ", style="dim")
            color = "green" if rate > 50 else "yellow" if rate > 25 else "red"
            stats_text.append(f"{rate:.1f}%\n", style=f"bold {color}")

        self.console.print()
        panel = Panel(
            stats_text,
            title="[bold white]Statistics[/bold white]",
            border_style="cyan",
            box=box.ROUNDED,
            padding=(1, 2),
        )
        self.console.print(panel)

        # Source breakdown
        if sources:
            self.console.print()
            src_table = Table(
                title="  Sources Breakdown",
                box=box.SIMPLE_HEAVY,
                border_style="dim",
                show_header=True,
                header_style="bold cyan",
            )
            src_table.add_column("Source", style="white", width=25)
            src_table.add_column("Count", style="cyan", justify="right", width=8)
            for src, count in sorted(sources.items(), key=lambda x: x[1], reverse=True):
                src_table.add_row(src, str(count))
            self.console.print(src_table)

        # Top countries
        if countries:
            self.console.print()
            top_countries = sorted(countries.items(), key=lambda x: x[1], reverse=True)[:10]
            cc_table = Table(
                title="  Top 10 Countries",
                box=box.SIMPLE_HEAVY,
                border_style="dim",
                show_header=True,
                header_style="bold cyan",
            )
            cc_table.add_column("Country", style="white", width=10)
            cc_table.add_column("Count", style="cyan", justify="right", width=8)
            for cc, count in top_countries:
                cc_table.add_row(cc, str(count))
            self.console.print(cc_table)

        # Protocol breakdown
        if protocols:
            self.console.print()
            proto_parts = [f"[cyan]{p.upper()}[/cyan]: {c}" for p, c in sorted(protocols.items())]
            self.console.print(f"  Protocols: {' | '.join(proto_parts)}")

    def get_progress(self) -> Progress:
        """Create a progress bar instance."""
        return Progress(
            SpinnerColumn(style="cyan"),
            TextColumn("[bold white]{task.description}[/bold white]"),
            BarColumn(bar_width=30, style="dim", complete_style="cyan", finished_style="green"),
            TextColumn("[cyan]{task.completed}/{task.total}[/cyan]"),
            TextColumn("[dim]*[/dim]"),
            TimeElapsedColumn(),
            console=self.console,
        )

    def scrape_summary(self, source_name: str, count: int, elapsed: float):
        """Show scraping result for a single source."""
        if count > 0:
            self.console.print(
                f"    [green]+[/green] [white]{source_name:<25}[/white] "
                f"[cyan]{count:>5}[/cyan] proxies  [dim]({elapsed:.1f}s)[/dim]"
            )
        else:
            self.console.print(
                f"    [red]x[/red] [dim]{source_name:<25}[/dim] "
                f"[red]  0[/red] proxies  [dim]({elapsed:.1f}s)[/dim]"
            )

    def validation_result(self, alive: int, dead: int, elapsed: float):
        """Show validation result summary."""
        total = alive + dead
        rate = (alive / total * 100) if total > 0 else 0

        self.console.print()
        self.console.print(f"  [bold white]Validation Complete[/bold white] [dim]({elapsed:.1f}s)[/dim]")
        self.console.print(f"    [green]* Alive:[/green]  {alive}")
        self.console.print(f"    [red]* Dead:[/red]   {dead}")
        self.console.print(f"    [cyan]* Rate:[/cyan]   {rate:.1f}%")

    def rotation_info(self, proxy, request_num: int):
        """Show current rotating proxy info."""
        self.console.print(
            f"  [dim]#{request_num}[/dim] -> "
            f"[cyan]{proxy.protocol}://{proxy.ip}:{proxy.port}[/cyan] "
            f"[dim]([/dim]{proxy.country_code}[dim])[/dim] "
            f"[dim]{proxy.speed:.0f}ms[/dim]"
        )

    def auto_refresh_status(self, interval: int, next_refresh: str, pool_size: int, alive: int):
        """Show auto-refresh daemon status."""
        self.console.print(
            f"\n  [bold cyan][~] Auto-Refresh Active[/bold cyan]"
            f"\n    Interval:     [white]{interval}s[/white] ({interval // 60}min)"
            f"\n    Next refresh: [white]{next_refresh}[/white]"
            f"\n    Pool size:    [white]{pool_size}[/white] total, [green]{alive}[/green] alive"
        )
