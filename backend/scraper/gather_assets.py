import asyncio
import datetime as dt
import os
from datetime import datetime

from core.models.location import MilitaryAirport
from scraper.core.db import AsyncSessionFactory, init_db
from scraper.extraction.client import ExtractionClient
from sqlalchemy import select

ASSETS_DIR = "/home/alex/SpaceATracker/backend/scraper/tests/extraction/assets"


async def main() -> None:
    """Populate PDF extract test assets."""
    await init_db()

    # Format: DDMMYYYY
    today_str = datetime.now(tz=dt.UTC).strftime("%d%m%Y")

    # Create subdirectories to organize assets
    os.makedirs(ASSETS_DIR, exist_ok=True)
    working_dir = os.path.join(ASSETS_DIR, today_str)
    os.makedirs(working_dir, exist_ok=True)

    async with AsyncSessionFactory() as session:
        stmt = select(MilitaryAirport).where(MilitaryAirport.website_url.is_not(None))
        result = await session.execute(stmt)
        terminals = result.scalars().all()

        print(f"Found {len(terminals)} terminals with a webpage.")

        async with ExtractionClient() as client:
            for terminal in terminals:
                url = str(terminal.website_url)
                print(f"Fetching {terminal.id} from {url}")
                try:
                    html = await client.fetch_terminal_page(url)
                    filename = f"{terminal.id}_{today_str}.html"
                    filepath = os.path.join(working_dir, filename)
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(html)
                    print(f"Saved {filepath}")
                except Exception as e:
                    print(f"Failed to fetch {terminal.id}: {e}")


if __name__ == "__main__":
    asyncio.run(main())
