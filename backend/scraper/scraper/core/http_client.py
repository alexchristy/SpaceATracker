import logging
from typing import Self

import aiohttp
from curl_cffi.requests import AsyncSession

logger = logging.getLogger(__name__)


class BaseHttpClient:
    """Abstract Asynchronous HTTP Client with browser TLS fingerprint impersonation."""

    def __init__(self) -> None:
        """Initialize the BaseHttpClient."""
        self.session: AsyncSession | None = None
        self.fallback_session: aiohttp.ClientSession | None = None

    async def __aenter__(self) -> Self:
        """Enter the async context manager and start the session."""
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: type | None,
    ) -> None:
        """Exit the async context manager and close the session."""
        await self.close()

    async def start(self) -> None:
        """Initialize the inner curl_cffi async session with Chrome impersonation."""
        if not self.session:
            self.session = AsyncSession(
                impersonate="chrome",
                timeout=30,
                verify=False,
            )

    async def close(self) -> None:
        """Close the inner session."""
        if self.session:
            await self.session.close()
            self.session = None
        if self.fallback_session:
            await self.fallback_session.close()
            self.fallback_session = None

    def _get_fallback_session(self) -> aiohttp.ClientSession:
        """Lazily initialize and return the aiohttp fallback session."""
        if not self.fallback_session:
            # We must pass ssl=False into aiohttp as well, due to the DoD CA certs issue
            connector = aiohttp.TCPConnector(ssl=False)
            self.fallback_session = aiohttp.ClientSession(connector=connector)
        return self.fallback_session

    def _check_session(self) -> None:
        """Check if the session is initialized before executing requests."""
        if not self.session:
            msg = "Client session is not initialized. Call start() first or use async with context."
            raise RuntimeError(msg)
