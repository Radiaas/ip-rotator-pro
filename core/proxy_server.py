"""
Local rotating proxy server.
Acts as a proxy gateway that rotates the upstream proxy for each request.
"""

import asyncio
import json
from typing import Optional
from core.models import ProxyPool
from core.rotator import IPRotator
from utils.display import Display


class ProxyServer:
    """
    Local TCP proxy server that forwards raw requests to rotating upstream proxies.
    Supports both HTTP and HTTPS (CONNECT) seamlessly by acting as a transparent TCP pipe.
    """

    def __init__(self, rotator: IPRotator, display: Optional[Display] = None,
                 host: str = "127.0.0.1", port: int = 8080):
        self.rotator = rotator
        self.display = display or Display()
        self.host = host
        self.port = port
        self.server = None
        self._request_count = 0

    async def handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle incoming client connection."""
        self._request_count += 1

        try:
            # Read the initial request chunk to check if it's a status request
            request_data = await reader.read(8192)
            if not request_data:
                writer.close()
                return

            # Check for status endpoint
            if request_data.startswith(b"GET /__status"):
                await self._serve_status(writer)
                return

            # Try connecting to upstream proxies with retries
            up_reader, up_writer = None, None
            connected_proxy = None
            
            for attempt in range(3):
                # Get an HTTP proxy
                proxy = None
                for _ in range(5):
                    p = self.rotator.get_proxy()
                    if not p:
                        break
                    if p.protocol in ("http", "https"):
                        proxy = p
                        break
                
                if not proxy:
                    break
                    
                try:
                    up_reader, up_writer = await asyncio.wait_for(
                        asyncio.open_connection(proxy.ip, proxy.port),
                        timeout=8.0
                    )
                    connected_proxy = proxy
                    break  # Success!
                except Exception:
                    self.rotator.report_failure(proxy)
                    continue

            if not up_writer or not connected_proxy:
                # No suitable proxy found or all attempts failed
                response = b"HTTP/1.1 503 Service Unavailable\r\n\r\nProxy connection failed."
                writer.write(response)
                await writer.drain()
                writer.close()
                return

            # We successfully connected. Forward the initial data.
            up_writer.write(request_data)
            await up_writer.drain()
            self.rotator.report_success(connected_proxy)

            # Start piping data in both directions
            await asyncio.gather(
                self._pipe(reader, up_writer),
                self._pipe(up_reader, writer),
                return_exceptions=True
            )

        except Exception:
            pass
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _pipe(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Pipe data from reader to writer."""
        try:
            while True:
                data = await reader.read(16384)
                if not data:
                    break
                writer.write(data)
                await writer.drain()
        except Exception:
            pass
        finally:
            try:
                writer.close()
            except Exception:
                pass

    async def _serve_status(self, writer: asyncio.StreamWriter):
        """Serve the JSON status payload."""
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

        body = json.dumps(status, indent=2, default=str).encode('utf-8')
        headers = (
            f"HTTP/1.1 200 OK\r\n"
            f"Content-Type: application/json\r\n"
            f"Connection: close\r\n"
            f"Content-Length: {len(body)}\r\n\r\n"
        )
        response = headers.encode('utf-8') + body
        writer.write(response)
        await writer.drain()
        writer.close()

    async def start(self):
        """Start the local TCP proxy server."""
        self.server = await asyncio.start_server(
            self.handle_client, self.host, self.port
        )

        self.display.console.print()
        self.display.success(f"[🌐] Proxy server started on {self.host}:{self.port}")
        self.display.info(f"Set your Android Wi-Fi or Proxy App to: {self.host}:{self.port}")
        self.display.info(f"Status endpoint: http://{self.host}:{self.port}/__status")
        self.display.info(f"Rotation strategy: {self.rotator.strategy}")
        self.display.console.print()
        self.display.info("Press Ctrl+C to stop the server")

    async def stop(self):
        """Stop the proxy server."""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.display.info("Proxy server stopped")
