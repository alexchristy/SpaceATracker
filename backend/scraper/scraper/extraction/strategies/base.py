"""Strategy Pattern Protocol for extracting PDF schedules from HTML pages."""

from typing import Protocol

from core.schemas.location import MilitaryAirportRead


class PDFExtractor(Protocol):
    """Protocol defining the interface for all PDF extraction strategies."""

    async def extract_pdf_url(
        self, html: str, terminal: MilitaryAirportRead
    ) -> str | None:
        """Extract the most recent schedule PDF URL from the given HTML content.

        Args:
            html: The raw HTML content of the terminal's page.
            terminal: The MilitaryAirport record for context (name, icao, etc).

        Returns:
            The absolute URL to the schedule PDF, or None if not found/unsupported by this strategy.
        """
        ...
