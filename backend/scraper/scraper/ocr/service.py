"""OCR service orchestrating extraction, processing, and persistence."""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

from core.models.flight import Flight

if TYPE_CHECKING:
    from core.models.terminal_document import TerminalDocument
    from sqlalchemy.ext.asyncio import AsyncSession

    from scraper.ocr.client import GeminiOCRClient
    from scraper.ocr.pipeline import FlightProcessingPipeline

logger = logging.getLogger(__name__)


class OCRService:
    """Orchestrates OCR extraction, pipeline, and DB persistence."""

    def __init__(
        self,
        db_session: AsyncSession,
        ocr_client: GeminiOCRClient,
        pipeline: FlightProcessingPipeline,
    ) -> None:
        """Initialize with dependencies.

        Args:
            db_session: Async database session.
            ocr_client: Gemini OCR client for extraction.
            pipeline: Processing pipeline for enrichment.
        """
        self._db = db_session
        self._ocr_client = ocr_client
        self._pipeline = pipeline

    async def process_document(
        self,
        document: TerminalDocument,
        raw_bytes: bytes,
    ) -> None:
        """Extract flights from a document and persist them.

        Args:
            document: The TerminalDocument DB record.
            raw_bytes: The raw file content.
        """
        extraction = await self._ocr_client.extract(
            file_bytes=raw_bytes,
            mime_type=document.mime_type,
        )

        processed = await self._pipeline.run(extraction)

        for flight_data in processed:
            flight = Flight(
                id=str(uuid.uuid4()),
                terminal_doc_id=document.id,
                origin_id=flight_data.origin_id,
                destination_id=flight_data.destination_id,
                roll_call_time=flight_data.roll_call_time,
                seats_available=flight_data.seats_available,
                seat_status=flight_data.seat_status,
                raw_seats=flight_data.raw_seats,
                raw_origin=flight_data.raw_origin,
                raw_destination=flight_data.raw_destination,
            )
            self._db.add(flight)

        await self._db.commit()

        logger.info(
            "OCR complete for doc %s: %d flights persisted",
            document.id,
            len(processed),
        )
