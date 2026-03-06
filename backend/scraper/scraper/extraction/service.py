"""Service handling the periodic extraction of documents from known terminals."""

import logging
from typing import TYPE_CHECKING

from core.models.location import MilitaryAirport
from scraper.extraction.chain import ExtractionChain
from scraper.extraction.client import ExtractionClient
from scraper.extraction.strategies.amc_image_link import AMCImageLinkExtractor
from scraper.extraction.strategies.amc_text_link import AMCTextLinkExtractor
from sqlalchemy import select

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


logger = logging.getLogger(__name__)


class ExtractionService:
    """Service handling the periodic extraction of documents from known terminals."""

    def __init__(self, db_session: AsyncSession) -> None:
        """Initialize with a database session."""
        self.db = db_session
        self.chain = ExtractionChain(
            strategies=[
                AMCTextLinkExtractor(),
                AMCImageLinkExtractor(),
            ]
        )

    async def run_extraction(self) -> None:
        """Execute the extraction workflow.

        1. Fetch all terminal URLs from DB.
        2. Download terminal HTML.
        3. Pass HTML through ExtractionChain.
        4. Log discovered document URLs.
        5. (Future) Download → hash → dedup → upload to MinIO → insert DB row.
        """
        logger.info("Starting Extraction Scraper Workflow...")

        # 1. Fetch terminals
        stmt = select(MilitaryAirport).where(MilitaryAirport.website_url.is_not(None))
        result = await self.db.execute(stmt)
        terminals = result.scalars().all()

        if not terminals:
            logger.warning("No terminals found with website URLs in the database.")
            return

        async with ExtractionClient() as client:
            for terminal in terminals:
                assert terminal.website_url is not None
                url = str(terminal.website_url)

                logger.debug("Processing terminal: %s (%s)", terminal.name, url)

                try:
                    html = await client.fetch_terminal_page(url)
                except Exception:
                    logger.exception("Failed to fetch HTML for %s", terminal.name)
                    continue

                extraction_result = await self.chain.execute(html, terminal)

                # Log the extracted document URLs.
                if extraction_result.schedule_72hr_url:
                    logger.info(
                        "72hr schedule for %s: %s",
                        terminal.name,
                        extraction_result.schedule_72hr_url,
                    )
                if extraction_result.schedule_30day_url:
                    logger.info(
                        "30-day schedule for %s: %s",
                        terminal.name,
                        extraction_result.schedule_30day_url,
                    )
                if extraction_result.rollcall_url:
                    logger.info(
                        "Rollcall for %s: %s",
                        terminal.name,
                        extraction_result.rollcall_url,
                    )

                # TODO: For each non-null URL:
                #   download → SHA-256 → compare latest hash for (terminal_id, doc_type)
                #   hash match → skip
                #   hash new → upload to MinIO → insert terminal_documents row

        logger.info("Extraction complete.")
