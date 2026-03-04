"""Extraction chain runner to process HTML against multiple fallback strategies."""

import logging
from collections.abc import Sequence

from core.schemas.location import MilitaryAirportRead
from scraper.extraction.strategies.base import PDFExtractor

logger = logging.getLogger(__name__)


class ExtractionChain:
    """Runs terminal HTML through a prioritized list of extractor strategies."""

    def __init__(self, strategies: Sequence[PDFExtractor]) -> None:
        """Initialize with a list of strategies to try in order."""
        self.strategies = strategies

    async def execute(self, html: str, terminal: MilitaryAirportRead) -> str | None:
        """Execute the chain of strategies against the HTML.
        Returns the first successfully extracted PDF URL.
        """
        for strategy in self.strategies:
            strategy_name = strategy.__class__.__name__
            try:
                pdf_url = await strategy.extract_pdf_url(html, terminal)
                if pdf_url:
                    logger.info(
                        "Strategy %s succeeded for %s", strategy_name, terminal.name
                    )
                    return pdf_url
            except Exception:
                logger.exception(
                    "Strategy %s failed with an error on %s",
                    strategy_name,
                    terminal.name,
                )
                # We continue to the next strategy even if one raises an exception
                continue

        logger.warning("All extraction strategies failed for %s", terminal.name)
        return None
