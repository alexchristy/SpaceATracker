"""Fallback strategy for extracting PDFs via Facebook links when standard parsing fails."""

import logging

from core.schemas.location import MilitaryAirportRead
from scraper.extraction.strategies.base import PDFExtractor

logger = logging.getLogger(__name__)


class FacebookExtractor(PDFExtractor):
    """Fallback strategy that attempts to find if the terminal links to a Facebook page
    and, if so, attempts to scrape the latest posts.
    Note: Requires an embedded browser or graph API which is currently omitted.
    This serves as a placeholder for the strategy pattern example.
    """

    async def extract_pdf_url(
        self, html: str, terminal: MilitaryAirportRead
    ) -> str | None:
        """Find the Facebook fallback link (stubbed)."""
        logger.debug(
            "FacebookExtractor tried for %s but is not fully implemented yet.",
            terminal.name,
        )
        return None
