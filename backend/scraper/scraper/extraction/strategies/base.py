"""Strategy Pattern Protocol for extracting document URLs from HTML pages."""

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from core.schemas.extraction import ExtractionResult
    from core.schemas.location import MilitaryAirportRead


class DocumentExtractor(Protocol):
    """Protocol defining the interface for all document extraction strategies."""

    async def extract_docs(
        self, html: str, terminal: MilitaryAirportRead
    ) -> ExtractionResult:
        """Extract document URLs from the given HTML content.

        Args:
            html: The raw HTML content of the terminal's page.
            terminal: The MilitaryAirport record for context (name, url, etc).

        Returns:
            An ExtractionResult with any discovered document URLs populated.
        """
        ...
