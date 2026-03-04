import logging
from typing import TYPE_CHECKING

from core.models.location import MilitaryAirport
from scraper.extraction.chain import ExtractionChain
from scraper.extraction.client import ExtractionClient
from scraper.extraction.strategies.facebook import FacebookExtractor
from scraper.extraction.strategies.standard import StandardAMCExtractor
from sqlalchemy import select

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


logger = logging.getLogger(__name__)


class ExtractionService:
    """Service handling the periodic extraction of PDFs from known terminals."""

    def __init__(self, db_session: AsyncSession) -> None:
        self.db = db_session
        # In the future, this list can be customized per terminal from the database
        self.chain = ExtractionChain(
            strategies=[
                StandardAMCExtractor(),
                FacebookExtractor(),
            ]
        )

    async def run_extraction(self) -> None:
        """Executes the 10-minute extraction workflow.
        1. Fetch all terminal URLs from DB.
        2. Download terminal HTML.
        3. Pass HTML through ExtractionChain.
        4. Download PDF if found.
        5. (Next Step) OCR PDF via Gemini.
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

                # We log this for now, but in a production 10 minute loop we'd parallelize
                # this via multiprocessing or `asyncio.gather`
                logger.debug("Processing terminal: %s (%s)", terminal.name, url)

                try:
                    html = await client.fetch_terminal_page(url)
                except Exception:
                    logger.exception("Failed to fetch HTML for %s", terminal.name)
                    continue

                pdf_url = await self.chain.execute(html, terminal)

                if pdf_url:
                    try:
                        pdf_bytes = await client.download_pdf(pdf_url)
                        logger.info(
                            "Successfully downloaded %d bytes of PDF for %s",
                            len(pdf_bytes),
                            terminal.name,
                        )
                        # TODO: Pass pdf_bytes to Gemini extractor
                    except Exception:
                        logger.exception("Failed to download PDF from %s", pdf_url)
                else:
                    logger.warning(
                        "Could not find a PDF schedule for %s", terminal.name
                    )

        logger.info("Extraction complete.")
