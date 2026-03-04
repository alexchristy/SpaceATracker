import logging

from scraper.core.config import settings
from scraper.core.http_client import BaseHttpClient

logger = logging.getLogger(__name__)


class DiscoveryClient(BaseHttpClient):
    """Asynchronous HTTP Client for fetching the main directory of Space-A terminals."""

    async def fetch_main_directory(self) -> str:
        """Fetch the HTML content of the main Space-A directory page."""
        self._check_session()
        if self.session is None:
            msg = "Client session is not initialized. Call start() first or use async with context."
            logger.exception(msg)
            raise RuntimeError(msg)

        logger.info("Fetching main directory from %s", settings.MAIN_DIRECTORY_URL)
        response = await self.session.get(settings.MAIN_DIRECTORY_URL)
        response.raise_for_status()
        return response.text
