"""Extraction chain runner to process HTML against multiple document extraction strategies."""

import logging
from typing import TYPE_CHECKING

from core.schemas.extraction import ExtractionResult

if TYPE_CHECKING:
    from collections.abc import Sequence

    from core.schemas.location import MilitaryAirportRead
    from scraper.extraction.strategies.base import DocumentExtractor

logger = logging.getLogger(__name__)


class ExtractionChain:
    """Runs terminal HTML through a prioritized list of extractor strategies.

    Merges results across strategies: for each field, the first non-None
    value wins. This allows different strategies to contribute different
    document types from the same page.
    """

    def __init__(self, strategies: Sequence[DocumentExtractor]) -> None:
        """Initialize with a list of strategies to try in order."""
        self.strategies = strategies

    async def execute(
        self, html: str, terminal: MilitaryAirportRead
    ) -> ExtractionResult:
        """Execute all strategies and merge their results.

        Returns an ExtractionResult populated with the first non-None URL
        discovered for each document type across all strategies.
        """
        merged: dict[str, str] = {}

        for strategy in self.strategies:
            strategy_name = strategy.__class__.__name__
            try:
                result = await strategy.extract_docs(html, terminal)
            except Exception:
                logger.exception(
                    "Strategy %s failed with an error on %s",
                    strategy_name,
                    terminal.name,
                )
                continue

            # Merge non-None fields from this result into the accumulator.
            for field in ("schedule_72hr_url", "schedule_30day_url", "rollcall_url"):
                value = getattr(result, field)
                if value is not None and field not in merged:
                    merged[field] = str(value)
                    logger.info(
                        "Strategy %s produced %s for %s",
                        strategy_name,
                        field,
                        terminal.name,
                    )

        if not merged:
            logger.warning(
                "All extraction strategies found nothing for %s", terminal.name
            )

        return ExtractionResult(**merged)
