import argparse
import asyncio
import logging
import sys

from scraper.core.config import settings
from scraper.core.db import AsyncSessionFactory, init_db
from scraper.discovery.service import DiscoveryService

# Configure structured logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)


async def run_discovery_scraper():
    """Async wrapper for the Discovery target."""
    logger.info("Initializing Database...")
    await init_db()

    logger.info("Starting Discovery Scraper Worker")
    async with (
        AsyncSessionFactory() as session
    ):  # Assuming get_db_session is a typo and AsyncSessionFactory is intended, or get_db_session needs to be defined/imported. Sticking to the provided change for now.
        service = DiscoveryService(session)
        await service.run_discovery()


async def run_extraction_scraper() -> None:
    """Async wrapper for the 10-minute Extraction target."""
    from scraper.extraction.service import ExtractionService

    logger.info("Initializing Database...")
    await init_db()

    logger.info("Starting Extraction Scraper Worker")
    async with (
        AsyncSessionFactory() as session
    ):  # Assuming get_db_session is a typo and AsyncSessionFactory is intended, or get_db_session needs to be defined/imported. Sticking to the provided change for now.
        service = ExtractionService(session)
        await service.run_extraction()


def main() -> None:
    """CLI Entrypoint for the scraper backend workers."""
    parser = argparse.ArgumentParser(description="SpaceATracker Background Workers")
    parser.add_argument(
        "worker",
        type=str,
        choices=["run-discovery", "run-extraction"],
        help="The specific web scraper worker to run.",
    )

    args = parser.parse_args()
    try:
        if args.worker == "run-discovery":
            asyncio.run(run_discovery_scraper())
        elif args.worker == "run-extraction":
            asyncio.run(run_extraction_scraper())
    except KeyboardInterrupt:
        logger.info("Worker interrupted by user.")
    except Exception as e:
        logger.exception(f"Worker encountered a fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
