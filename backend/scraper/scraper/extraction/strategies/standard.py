"""Standard strategy for extracting PDFs from typical AMC terminal websites."""

import logging
from urllib.parse import urljoin

from core.schemas.location import MilitaryAirportRead
from scraper.extraction.strategies.base import PDFExtractor
from selectolax.parser import HTMLParser

logger = logging.getLogger(__name__)


class StandardAMCExtractor(PDFExtractor):
    """Strategy for standard Air Mobility Command (AMC) sites.
    Typically these use unstructured <a> tags linking to /Portals/ files.
    """

    async def extract_pdf_url(
        self, html: str, terminal: MilitaryAirportRead
    ) -> str | None:
        """Find the most likely schedule PDF link in the HTML."""
        tree = HTMLParser(html)

        # Standard heuristics for AMC Sites
        for a_tag in tree.css("a"):
            href = a_tag.attributes.get("href")
            if not href:
                continue

            text = a_tag.text(strip=True).lower()
            href_lower = href.lower()

            # We are looking for links that indicate a schedule and end in .pdf
            # Many times the text contains "schedule" or "roll call"
            if ".pdf" in href_lower and (
                "schedule" in text or "roll" in text or "flight" in text
            ):
                # Ensure the URL is absolute
                if terminal.website_url:
                    absolute_url = urljoin(str(terminal.website_url), href)
                    logger.debug(
                        "StandardAMCExtractor found PDF %s on %s",
                        absolute_url,
                        terminal.name,
                    )
                    return absolute_url

        return None
