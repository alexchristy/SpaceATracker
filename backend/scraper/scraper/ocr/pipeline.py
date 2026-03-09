"""Processing pipeline for enriching extracted flight data."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from core.schemas.flight import ProcessedFlight

if TYPE_CHECKING:
    from core.schemas.flight import FlightExtractionList

logger = logging.getLogger(__name__)


@runtime_checkable
class FlightProcessor(Protocol):
    """Interface for a flight data processor."""

    async def process_batch(
        self, flights: list[ProcessedFlight]
    ) -> list[ProcessedFlight]:
        """Process a batch of flights and return the result.

        Args:
            flights: The batch of processed flights to enrich.

        Returns:
            The enriched batch.
        """
        ...


class FlightProcessingPipeline:
    """Runs extracted flights through a chain of processors."""

    def __init__(self, processors: list[FlightProcessor] | None = None) -> None:
        """Initialize with an optional list of processors.

        Args:
            processors: Ordered list of processors to apply.
        """
        self._processors = processors or []

    async def run(self, extraction: FlightExtractionList) -> list[ProcessedFlight]:
        """Convert extractions to ProcessedFlight and run pipeline.

        Args:
            extraction: The raw extraction list from the LLM.

        Returns:
            The enriched list of processed flights.
        """
        batch = [
            ProcessedFlight(**flight.model_dump()) for flight in extraction.flights
        ]

        for processor in self._processors:
            batch = await processor.process_batch(batch)

        logger.info(
            "Pipeline complete: %d flights through %d processors",
            len(batch),
            len(self._processors),
        )
        return batch
