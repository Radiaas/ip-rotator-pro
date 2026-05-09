#!/usr/bin/env python3
"""
IP Rotator Pro — All-in-one Proxy Scraper, Validator & Rotator
==============================================================
Scrape, validate, rotate, and manage proxy IPs automatically.
GitHub-ready. Termux-compatible. Dead IP detection. Auto-refresh.

Usage:
    python rotator.py scrape                  # Scrape proxies from all sources
    python rotator.py scrape --validate       # Scrape + validate
    python rotator.py validate                # Validate existing pool
    python rotator.py export --format txt     # Export alive proxies
    python rotator.py server                  # Start rotating proxy server
    python rotator.py run                     # Full pipeline: scrape → validate → rotate → auto-refresh
    python rotator.py dashboard               # Show proxy pool dashboard
"""

import argparse
import asyncio
import json
import os
import signal
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.models import ProxyPool
from core.scraper import ProxyScraper
from core.validator import ProxyValidator
from core.rotator import IPRotator
from core.proxy_server import ProxyServer
from utils.display import Display
from utils.exporter import Exporter


def load_config(config_path: str = "config.json") -> dict:
    """Load configuration from JSON file."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(script_dir, config_path)

    default_config = {
        "validation": {
            "timeout": 10,
            "max_concurrent": 100,
            "judge_urls": [
                "http://httpbin.org/ip",
                "http://api.ipify.org",
                "http://icanhazip.com",
                "http://ifconfig.me/ip",
                "http://checkip.amazonaws.com",
            ],
            "retry_count": 2,
        },
        "rotation": {
            "strategy": "smart",
            "max_fail_count": 3,
            "auto_refresh_interval": 180,
        },
        "scraping": {
            "enabled_sources": ["proxyscrape", "github_lists", "geonode", "web_scraper"],
        },
        "server": {
            "host": "127.0.0.1",
            "port": 8080,
        },
        "export": {
            "output_dir": "output",
            "default_format": "txt",
        },
    }

    if os.path.exists(config_file):
        try:
            with open(config_file, "r") as f:
                user_config = json.load(f)

            # Deep merge
            for key in user_config:
                if key in default_config and isinstance(default_config[key], dict):
                    default_config[key].update(user_config[key])
                else:
                    default_config[key] = user_config[key]
        except Exception:
            pass

    return default_config


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="rotator.py",
        description="IP Rotator Pro -- Proxy Scraper, Validator & Rotator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python rotator.py scrape                        Scrape from all sources
  python rotator.py scrape --source proxyscrape   Scrape from specific source
  python rotator.py scrape --validate --export    Scrape -> Validate -> Export
  python rotator.py validate --timeout 5          Validate with 5s timeout
  python rotator.py export --format json          Export to JSON
  python rotator.py server --port 9090            Start proxy server on port 9090
  python rotator.py run                           Full auto pipeline
  python rotator.py run --interval 180            Auto-refresh every 3 minutes
  python rotator.py dashboard                     Show pool stats
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # === SCRAPE ===
    scrape_parser = subparsers.add_parser("scrape", help="Scrape proxies from sources")
    scrape_parser.add_argument(
        "--source", "-s",
        choices=["proxyscrape", "github_lists", "geonode", "web_scraper", "all"],
        default="all",
        help="Source to scrape from (default: all)",
    )
    scrape_parser.add_argument(
        "--validate", "-v", action="store_true",
        help="Validate proxies after scraping",
    )
    scrape_parser.add_argument(
        "--export", "-e", nargs="?", const="txt",
        choices=["txt", "csv", "json"],
        help="Export results after scraping (default: txt)",
    )
    scrape_parser.add_argument(
        "--timeout", "-t", type=int, default=None,
        help="Validation timeout in seconds",
    )

    # === VALIDATE ===
    validate_parser = subparsers.add_parser("validate", help="Validate proxy pool")
    validate_parser.add_argument(
        "--timeout", "-t", type=int, default=None,
        help="Timeout per proxy in seconds",
    )
    validate_parser.add_argument(
        "--concurrent", "-c", type=int, default=None,
        help="Max concurrent validations",
    )
    validate_parser.add_argument(
        "--remove-dead", "-r", action="store_true",
        help="Remove dead proxies from pool",
    )

    # === EXPORT ===
    export_parser = subparsers.add_parser("export", help="Export proxies")
    export_parser.add_argument(
        "--format", "-f",
        choices=["txt", "csv", "json"],
        default=None,
        help="Export format",
    )
    export_parser.add_argument(
        "--alive-only", "-a", action="store_true", default=True,
        help="Export only alive proxies (default: True)",
    )
    export_parser.add_argument(
        "--protocol", "-p",
        choices=["http", "https", "socks4", "socks5"],
        help="Filter by protocol",
    )
    export_parser.add_argument(
        "--country", help="Filter by country code (e.g., US, ID, SG)",
    )

    # === SERVER ===
    server_parser = subparsers.add_parser("server", help="Start rotating proxy server")
    server_parser.add_argument(
        "--host", default=None,
        help="Server host (default: 127.0.0.1)",
    )
    server_parser.add_argument(
        "--port", "-p", type=int, default=None,
        help="Server port (default: 8080)",
    )
    server_parser.add_argument(
        "--strategy",
        choices=["round_robin", "random", "smart", "fastest"],
        default=None,
        help="Rotation strategy",
    )
    server_parser.add_argument(
        "--no-auto-refresh", action="store_true",
        help="Disable auto-refresh",
    )
    server_parser.add_argument(
        "--interval", "-i", type=int, default=None,
        help="Auto-refresh interval in seconds (default: 180)",
    )

    # === RUN (full pipeline) ===
    run_parser = subparsers.add_parser("run", help="Full pipeline: scrape -> validate -> auto-refresh")
    run_parser.add_argument(
        "--interval", "-i", type=int, default=None,
        help="Auto-refresh interval in seconds (default: 180 = 3 min)",
    )
    run_parser.add_argument(
        "--strategy",
        choices=["round_robin", "random", "smart", "fastest"],
        default=None,
        help="Rotation strategy",
    )
    run_parser.add_argument(
        "--server", "-s", action="store_true",
        help="Also start the proxy server",
    )
    run_parser.add_argument(
        "--port", "-p", type=int, default=None,
        help="Server port (if --server is used)",
    )
    run_parser.add_argument(
        "--export", "-e", nargs="?", const="txt",
        choices=["txt", "csv", "json"],
        help="Export alive proxies each refresh cycle",
    )
    run_parser.add_argument(
        "--timeout", "-t", type=int, default=None,
        help="Validation timeout in seconds",
    )

    # === DASHBOARD ===
    subparsers.add_parser("dashboard", help="Show pool statistics dashboard")

    return parser


async def cmd_scrape(args, config, display):
    """Handle the 'scrape' command."""
    pool = ProxyPool()

    sources = config["scraping"]["enabled_sources"]
    if args.source and args.source != "all":
        sources = [args.source]

    scraper = ProxyScraper(pool, display, enabled_sources=sources)
    await scraper.scrape_all()

    # Validate if requested
    if args.validate:
        timeout = args.timeout or config["validation"]["timeout"]
        concurrent = config["validation"]["max_concurrent"]
        validator = ProxyValidator(
            pool, display,
            timeout=timeout,
            max_concurrent=concurrent,
            retry_count=config["validation"]["retry_count"],
        )
        await validator.validate_all(remove_dead=True)

    # Show stats
    pool.update_stats()
    display.stats_panel(pool.stats)

    # Show top proxies
    alive = pool.alive_proxies
    if alive:
        pool.sort_by_speed()
        display.proxy_table(pool.alive_proxies, title=f"Alive Proxies ({len(alive)} total)")

    # Export if requested
    if args.export:
        exporter = Exporter(config["export"]["output_dir"])
        proxies_to_export = pool.alive_proxies if args.validate else pool.proxies
        filename = exporter.export(proxies_to_export, fmt=args.export)
        display.success(f"Exported {len(proxies_to_export)} proxies to: {filename}")


async def cmd_validate(args, config, display):
    """Handle the 'validate' command — scrape first then validate."""
    pool = ProxyPool()

    # First scrape to populate pool
    display.info("Scraping proxies before validation...")
    scraper = ProxyScraper(pool, display, enabled_sources=config["scraping"]["enabled_sources"])
    await scraper.scrape_all()

    if pool.size == 0:
        display.error("No proxies scraped! Cannot validate empty pool.")
        return

    timeout = args.timeout or config["validation"]["timeout"]
    concurrent = args.concurrent or config["validation"]["max_concurrent"]

    validator = ProxyValidator(
        pool, display,
        timeout=timeout,
        max_concurrent=concurrent,
        retry_count=config["validation"]["retry_count"],
    )
    await validator.validate_all(remove_dead=args.remove_dead)

    # Show results
    pool.update_stats()
    display.stats_panel(pool.stats)

    alive = pool.alive_proxies
    if alive:
        pool.sort_by_speed()
        display.proxy_table(alive, title=f"Alive Proxies ({len(alive)} total)")


async def cmd_export(args, config, display):
    """Handle the 'export' command — scrape + validate then export."""
    pool = ProxyPool()

    # Scrape and validate
    display.info("Scraping and validating proxies for export...")
    scraper = ProxyScraper(pool, display, enabled_sources=config["scraping"]["enabled_sources"])
    await scraper.scrape_all()

    validator = ProxyValidator(
        pool, display,
        timeout=config["validation"]["timeout"],
        max_concurrent=config["validation"]["max_concurrent"],
    )
    await validator.validate_all(remove_dead=True)

    # Apply filters
    proxies = pool.alive_proxies

    if args.protocol:
        proxies = [p for p in proxies if p.protocol == args.protocol]
        display.info(f"Filtered by protocol: {args.protocol} ({len(proxies)} proxies)")

    if args.country:
        proxies = [p for p in proxies if p.country_code.upper() == args.country.upper()]
        display.info(f"Filtered by country: {args.country} ({len(proxies)} proxies)")

    if not proxies:
        display.warning("No proxies match the filter criteria!")
        return

    # Export
    fmt = args.format or config["export"]["default_format"]
    exporter = Exporter(config["export"]["output_dir"])
    filename = exporter.export(proxies, fmt=fmt)
    display.success(f"Exported {len(proxies)} proxies to: {filename}")


async def cmd_server(args, config, display):
    """Handle the 'server' command."""
    pool = ProxyPool()

    strategy = args.strategy or config["rotation"]["strategy"]
    interval = args.interval or config["rotation"]["auto_refresh_interval"]

    scraper = ProxyScraper(pool, display, enabled_sources=config["scraping"]["enabled_sources"])
    validator = ProxyValidator(
        pool, display,
        timeout=config["validation"]["timeout"],
        max_concurrent=config["validation"]["max_concurrent"],
        retry_count=config["validation"]["retry_count"],
    )
    rotator = IPRotator(
        pool, scraper, validator, display,
        strategy=strategy,
        max_fail_count=config["rotation"]["max_fail_count"],
        auto_refresh_interval=interval,
    )

    # Initial load
    await rotator.initial_load()

    if pool.alive_count == 0:
        display.error("No alive proxies! Server cannot start without proxies.")
        display.info("Try running: python rotator.py scrape --validate")
        return

    # Start auto-refresh unless disabled
    if not args.no_auto_refresh:
        rotator.start_auto_refresh()

    # Start server
    host = args.host or config["server"]["host"]
    port = args.port or config["server"]["port"]
    server = ProxyServer(rotator, display, host=host, port=port)

    await server.start()

    # Keep running until Ctrl+C
    try:
        while True:
            await asyncio.sleep(1)
    except (KeyboardInterrupt, asyncio.CancelledError):
        display.console.print()
        display.info("Shutting down...")
        rotator.stop_auto_refresh()
        await server.stop()


async def cmd_run(args, config, display):
    """Handle the 'run' command — full pipeline with auto-refresh."""
    pool = ProxyPool()

    strategy = args.strategy or config["rotation"]["strategy"]
    interval = args.interval or config["rotation"]["auto_refresh_interval"]
    timeout = args.timeout or config["validation"]["timeout"]

    scraper = ProxyScraper(pool, display, enabled_sources=config["scraping"]["enabled_sources"])
    validator = ProxyValidator(
        pool, display,
        timeout=timeout,
        max_concurrent=config["validation"]["max_concurrent"],
        retry_count=config["validation"]["retry_count"],
    )
    rotator = IPRotator(
        pool, scraper, validator, display,
        strategy=strategy,
        max_fail_count=config["rotation"]["max_fail_count"],
        auto_refresh_interval=interval,
    )

    # Initial load
    alive_count = await rotator.initial_load()

    # Export if requested
    if args.export and alive_count > 0:
        exporter = Exporter(config["export"]["output_dir"])
        filename = exporter.export(pool.alive_proxies, fmt=args.export)
        display.success(f"Exported {alive_count} proxies to: {filename}")

    # Show proxy table
    if alive_count > 0:
        display.proxy_table(pool.alive_proxies, title=f"Alive Proxies ({alive_count} total)")

    # Start proxy server if requested
    server = None
    if args.server:
        port = args.port or config["server"]["port"]
        host = config["server"]["host"]
        server = ProxyServer(rotator, display, host=host, port=port)
        await server.start()

    # Start auto-refresh
    rotator.start_auto_refresh()

    display.console.print()
    display.info(f"IP Rotator Pro is running!")
    display.info(f"   Strategy: {strategy}")
    display.info(f"   Auto-refresh: every {interval}s ({interval // 60}min {interval % 60}s)")
    display.info(f"   Pool: {pool.alive_count} alive proxies")
    if server:
        display.info(f"   Proxy server: http://{config['server']['host']}:{args.port or config['server']['port']}")
    display.console.print()
    display.info("Press Ctrl+C to stop")

    # Keep running
    try:
        cycle = 0
        while True:
            await asyncio.sleep(30)
            cycle += 1

            # Periodic status update every 2 minutes
            if cycle % 4 == 0:
                pool.update_stats()
                display.console.print(
                    f"  [dim]{datetime.now().strftime('%H:%M:%S')}[/dim] "
                    f"Pool: [green]{pool.alive_count}[/green] alive / "
                    f"[white]{pool.size}[/white] total | "
                    f"Requests: [cyan]{rotator._request_count}[/cyan]"
                )

    except (KeyboardInterrupt, asyncio.CancelledError):
        display.console.print()
        display.info("Shutting down gracefully...")

        rotator.stop_auto_refresh()

        if server:
            await server.stop()

        # Final export
        if args.export and pool.alive_count > 0:
            exporter = Exporter(config["export"]["output_dir"])
            filename = exporter.export(pool.alive_proxies, fmt=args.export)
            display.success(f"Final export: {filename}")

        # Final stats
        pool.update_stats()
        display.stats_panel(pool.stats)
        display.success("IP Rotator Pro stopped. See you!")


async def cmd_dashboard(args, config, display):
    """Handle the 'dashboard' command — scrape + validate and show stats."""
    pool = ProxyPool()

    scraper = ProxyScraper(pool, display, enabled_sources=config["scraping"]["enabled_sources"])
    await scraper.scrape_all()

    validator = ProxyValidator(
        pool, display,
        timeout=config["validation"]["timeout"],
        max_concurrent=config["validation"]["max_concurrent"],
    )
    await validator.validate_all(remove_dead=True)

    # Full stats
    pool.update_stats()
    display.stats_panel(pool.stats)

    # Show proxy table
    alive = pool.alive_proxies
    if alive:
        pool.sort_by_speed()
        display.proxy_table(alive, title=f"Top Alive Proxies ({len(alive)} total)")

    # Summary
    display.console.print()
    display.info(f"Dashboard generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def main():
    """Main entry point."""
    display = Display()
    display.banner()

    parser = build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        display.console.print()
        display.info("Use 'python rotator.py <command> --help' for command-specific help")
        display.info("Quick start: python rotator.py run")
        sys.exit(0)

    config = load_config()

    # Map commands to handlers
    commands = {
        "scrape": cmd_scrape,
        "validate": cmd_validate,
        "export": cmd_export,
        "server": cmd_server,
        "run": cmd_run,
        "dashboard": cmd_dashboard,
    }

    handler = commands.get(args.command)
    if not handler:
        parser.print_help()
        sys.exit(1)

    # Run the async command
    try:
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

        asyncio.run(handler(args, config, display))

    except KeyboardInterrupt:
        display.console.print()
        display.info("Interrupted by user. Goodbye!")
        sys.exit(0)
    except Exception as e:
        display.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
