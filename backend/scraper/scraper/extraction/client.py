import logging

from scraper.core.http_client import BaseHttpClient

logger = logging.getLogger(__name__)


class ExtractionClient(BaseHttpClient):
    """Asynchronous HTTP Client for fetching individual terminal pages and downloading PDFs."""

    async def fetch_terminal_page(self, url: str) -> str:
        """Fetch the HTML content of an individual terminal's page."""
        self._check_session()
        assert self.session is not None

        logger.info("Fetching terminal page from %s", url)
        response = await self.session.get(url)
        response.raise_for_status()
        return response.text

    async def download_pdf(self, pdf_url: str) -> bytes:
        """Download the raw bytes of the schedule PDF."""
        self._check_session()
        assert self.session is not None

        logger.info("Downloading PDF from %s", pdf_url)
        response = await self.session.get(pdf_url)
        response.raise_for_status()
        return response.content
