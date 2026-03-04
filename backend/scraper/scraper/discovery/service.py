import logging
from typing import TYPE_CHECKING

from core.models.location import MilitaryAirport
from scraper.discovery.client import DiscoveryClient
from scraper.discovery.parser import DirectoryParser
from sqlalchemy.dialects.postgresql import insert

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class DiscoveryService:
    """Service class linking connection, parsing, and database transactions."""

    def __init__(self, db_session: AsyncSession) -> None:
        self.db = db_session

    async def run_discovery(self) -> None:
        """Executes the main directory discovery workflow.

        1. Fetches HTML.
        2. Parses MilitaryAirports.
        3. Upserts to PostgreSQL.
        """
        logger.info("Starting Discovery Scraper Workflow...")

        async with DiscoveryClient() as client:
            try:
                html = await client.fetch_main_directory()
            except Exception:
                logger.exception("Failed to fetch directory")
                # For development/testing: graceful downgrade to empty text
                html = ""

        if not html:
            logger.warning("No HTML content to parse. Exiting discovery.")
            return

        parser = DirectoryParser(html)
        terminals_added = 0

        for terminal_create in parser.extract_terminals():
            # Create a dictionary of the Pydantic model for SQLAlchemy
            stmt = insert(MilitaryAirport).values(
                id=terminal_create.id,
                name=terminal_create.name,
                raw_location=terminal_create.raw_location,
                location_type=terminal_create.location_type,
                website_url=str(terminal_create.website_url)
                if terminal_create.website_url
                else None,
                latitude=terminal_create.latitude,
                longitude=terminal_create.longitude,
                timezone=str(terminal_create.timezone)
                if terminal_create.timezone
                else None,
                country=terminal_create.country,
                state_or_province=terminal_create.state_or_province,
            )

            # On conflict (ID exists), update the website_url and name in case they changed
            upsert_stmt = stmt.on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "name": stmt.excluded.name,
                    "raw_location": stmt.excluded.raw_location,
                    "website_url": stmt.excluded.website_url,
                },
            )

            try:
                async with self.db.begin_nested():
                    await self.db.execute(upsert_stmt)
                terminals_added += 1
            except Exception:
                logger.exception("Failed to upsert terminal '%s'", terminal_create.name)
                continue

        await self.db.commit()
        logger.info(
            "Discovery complete. Processed %s MilitaryAirports.", terminals_added
        )
