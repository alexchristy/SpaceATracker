import logging

from core.schemas.exceptions import DocumentDownloadError
from curl_cffi.requests.exceptions import ConnectionError as CurlConnectionError
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

    async def download_document(self, doc_url: str) -> bytes:
        """Download the raw bytes of the document, falling back if SSL renegotiation fails."""
        self._check_session()
        assert self.session is not None

        logger.info("Downloading document from %s", doc_url)
        try:
            response = await self.session.get(doc_url)
            response.raise_for_status()
            return response.content
        except CurlConnectionError as e:
            # Check if this is the specific BoringSSL NO_RENEGOTIATION error
            # This happens with amc.usaf.afpims.mil which tries to renegotiate TLS mid-stream
            error_str = str(e)
            if "curl: (56)" in error_str or "NO_RENEGOTIATION" in error_str:
                msg = f"Link is broken or inaccessible (SSL/403): {doc_url}"
                raise DocumentDownloadError(msg) from e

            # If it's a different connection error (timeout, unreachable), bubble it up
            raise
