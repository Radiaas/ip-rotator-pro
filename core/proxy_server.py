"""
Local rotating proxy server.
Acts as a proxy gateway that rotates the upstream proxy for each request.
"""

import asyncio
from aiohttp import web, ClientSession, ClientTimeout
from typing import Optional
from core.models import ProxyPool
from core.rotator import IPRotator
from utils.display import Display


class ProxyServer:
    """
    Local HTTP proxy server that forwards requests through rotating proxies.
    Set your browser/app proxy to localhost:8080 and every request will use a different IP.
    """

    def __init__(self, rotator: IPRotator, display: Optional[Display] = None,
                 host: str = "127.0.0.1", port: int = 8080):
        self.rotator = rotator
        self.display = display or Display()
        self.host = host
        self.port = port
        self._app = None
        self._runner = None
        self._request_count = 0

    async def handle_request(self, request: web.Request) -> web.Response:
        """Handle incoming proxy request and forward through a rotated proxy."""
        self._request_count += 1

        # Get next proxy from rotator
        proxy = self.rotator.get_proxy()
        if not proxy:
            return web.Response(
                status=503,
                text="No alive proxies available. Pool is empty.",
                content_type="text/plain",
            )

        # Build target URL
        target_url = str(request.url)
        if not target_url.startswith("http"):
            target_url = f"http://{request.host}{request.path_qs}"

        proxy_url = f"http://{proxy.ip}:{proxy.port}"

        try:
            timeout = ClientTimeout(total=15)
            async with ClientSession(timeout=timeout) as session:
                # Forward headers (excluding hop-by-hop)
                headers = dict(request.headers)
                for hop_header in ["Connection", "Keep-Alive", "Proxy-Authenticate",
                                   "Proxy-Authorization", "TE", "Trailers",
                                   "Transfer-Encoding", "Upgrade", "Proxy-Connection"]:
                    headers.pop(hop_header, None)

                # Read request body
                body = await request.read()

                async with session.request(
                    method=request.method,
                    url=target_url,
                    headers=headers,
                    data=body if body else None,
                    proxy=proxy_url,
                    ssl=False,
                    allow_redirects=False,
                ) as resp:
                    # Read response
                    resp_body = await resp.read()

                    # Report success
                    self.rotator.report_success(proxy)

                    # Build response
                    response_headers = dict(resp.headers)
                    for hop_header in ["Content-Encoding", "Transfer-Encoding", "Connection"]:
                        response_headers.pop(hop_header, None)

                    return web.Response(
                        status=resp.status,
                        body=resp_body,
                        headers=response_headers,
                    )

        except Exception as e:
            self.rotator.report_failure(proxy)

            # Try to get another proxy and retry once
            retry_proxy = self.rotator.get_proxy()
            if retry_proxy:
                try:
                    retry_proxy_url = f"http://{retry_proxy.ip}:{retry_proxy.port}"
                    timeout = ClientTimeout(total=15)
                    async with ClientSession(timeout=timeout) as session:
                        async with session.request(
                            method=request.method,
                            url=target_url,
                            proxy=retry_proxy_url,
                            ssl=False,
                            allow_redirects=False,
                        ) as resp:
                            resp_body = await resp.read()
                            self.rotator.report_success(retry_proxy)
                            return web.Response(
                                status=resp.status,
                                body=resp_body,
                            )
                except Exception:
                    self.rotator.report_failure(retry_proxy)

            return web.Response(
                status=502,
                text=f"Proxy request failed: {str(e)}",
                content_type="text/plain",
            )

    async def handle_status(self, request: web.Request) -> web.Response:
        """API endpoint to check server and pool status."""
        pool = self.rotator.pool
        pool.update_stats()

        status = {
            "server": "running",
            "requests_handled": self._request_count,
            "strategy": self.rotator.strategy,
            "auto_refresh_interval": self.rotator.auto_refresh_interval,
            "pool": {
                "total": pool.size,
                "alive": pool.alive_count,
                "stats": pool.stats,
            },
        }

        import json
        return web.Response(
            status=200,
            text=json.dumps(status, indent=2, default=str),
            content_type="application/json",
        )

    async def start(self):
        """Start the local proxy server."""
        self._app = web.Application()

        # Status endpoint
        self._app.router.add_get("/__status", self.handle_status)
        self._app.router.add_get("/__status/", self.handle_status)

        # Catch-all for proxy requests
        self._app.router.add_route("*", "/{path:.*}", self.handle_request)

        self._runner = web.AppRunner(self._app, access_log=None)
        await self._runner.setup()

        site = web.TCPSite(self._runner, self.host, self.port)
        await site.start()

        self.display.console.print()
        self.display.success(f"🌐 Proxy server started on {self.host}:{self.port}")
        self.display.info(f"Set your browser/app proxy to: http://{self.host}:{self.port}")
        self.display.info(f"Status endpoint: http://{self.host}:{self.port}/__status")
        self.display.info(f"Rotation strategy: {self.rotator.strategy}")
        self.display.console.print()
        self.display.info("Press Ctrl+C to stop the server")

    async def stop(self):
        """Stop the proxy server."""
        if self._runner:
            await self._runner.cleanup()
            self.display.info("Proxy server stopped")
