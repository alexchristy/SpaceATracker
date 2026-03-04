import logging
from typing import Self

from curl_cffi.requests import AsyncSession

logger = logging.getLogger(__name__)


class BaseHttpClient:
    """Abstract Asynchronous HTTP Client with browser TLS fingerprint impersonation."""

    def __init__(self) -> None:
        """Initialize the BaseHttpClient."""
        self.session: AsyncSession | None = None

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
            )

    async def close(self) -> None:
        """Close the inner session."""
        if self.session:
            await self.session.close()
            self.session = None

    def _check_session(self) -> None:
        """Check if the session is initialized before executing requests."""
        if not self.session:
            msg = "Client session is not initialized. Call start() first or use async with context."
            raise RuntimeError(msg)
