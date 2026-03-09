"""Tests for the OCR service layer."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from core.models.terminal_document import TerminalDocument
from core.schemas.flight import FlightExtraction, FlightExtractionList, ProcessedFlight
from scraper.ocr.client import GeminiOCRClient
from scraper.ocr.pipeline import FlightProcessingPipeline
from scraper.ocr.service import OCRService


@pytest.fixture()
def mock_db_session() -> AsyncMock:
    """Provide a mocked async database session."""
    session = AsyncMock()
    # session.add() is synchronous in SQLAlchemy
    session.add = MagicMock()
    return session


@pytest.fixture()
def sample_extraction_list() -> FlightExtractionList:
    """Provide a sample FlightExtractionList for testing."""
    return FlightExtractionList(
        flights=[
            FlightExtraction(
                roll_call_time=datetime(2026, 3, 10, 14, 0, tzinfo=UTC),
                raw_seats="20F",
                raw_origin="Travis AFB",
                raw_destination="Ramstein AB",
            ),
            FlightExtraction(
                roll_call_time=datetime(2026, 3, 11, 8, 30, tzinfo=UTC),
                raw_seats="TBD",
                raw_origin="Dover AFB",
                raw_destination="Incirlik AB",
            ),
        ]
    )


@pytest.fixture()
def sample_terminal_document() -> TerminalDocument:
    """Provide a sample TerminalDocument for testing."""
    return TerminalDocument(
        id=42,
        terminal_id="travis-afb",
        doc_type="schedule_72hr",
        url="http://example.com/schedule.pdf",
        content_hash="abc123",
        storage_key="terminals/travis-afb/schedule_72hr/abc123.pdf",
        mime_type="application/pdf",
        scraped_at=datetime.now(UTC),
    )


class TestGeminiOCRClient:
    """Tests for the GeminiOCRClient wrapper."""

    @pytest.mark.asyncio()
    async def test_extract_returns_extraction_list(
        self,
        sample_extraction_list: FlightExtractionList,
    ) -> None:
        """Client returns a FlightExtractionList from raw bytes."""
        mock_genai_client = MagicMock()

        # Mock the async generate_content response
        mock_response = MagicMock()
        mock_response.parsed = sample_extraction_list
        mock_generate = AsyncMock(return_value=mock_response)
        mock_genai_client.aio.models.generate_content = mock_generate

        client = GeminiOCRClient(genai_client=mock_genai_client)
        result = await client.extract(
            file_bytes=b"fake pdf bytes",
            mime_type="application/pdf",
        )

        assert isinstance(result, FlightExtractionList)
        assert len(result.flights) == 2
        assert result.flights[0].raw_origin == "Travis AFB"

    @pytest.mark.asyncio()
    async def test_extract_calls_genai_with_correct_schema(
        self,
        sample_extraction_list: FlightExtractionList,
    ) -> None:
        """Client passes FlightExtractionList as response schema."""
        mock_genai_client = MagicMock()
        mock_response = MagicMock()
        mock_response.parsed = sample_extraction_list
        mock_generate = AsyncMock(return_value=mock_response)
        mock_genai_client.aio.models.generate_content = mock_generate

        client = GeminiOCRClient(genai_client=mock_genai_client)
        await client.extract(
            file_bytes=b"fake pdf bytes",
            mime_type="application/pdf",
        )

        call_kwargs = mock_generate.call_args
        config = call_kwargs.kwargs.get("config")
        assert config is not None
        assert config.response_schema == FlightExtractionList


class TestFlightProcessingPipeline:
    """Tests for the FlightProcessingPipeline."""

    @pytest.mark.asyncio()
    async def test_empty_pipeline_passes_through(
        self,
        sample_extraction_list: FlightExtractionList,
    ) -> None:
        """Pipeline with no processors passes data through."""
        pipeline = FlightProcessingPipeline(processors=[])
        result = await pipeline.run(sample_extraction_list)

        assert len(result) == 2
        assert all(isinstance(f, ProcessedFlight) for f in result)
        assert result[0].raw_origin == "Travis AFB"
        assert result[1].raw_origin == "Dover AFB"

    @pytest.mark.asyncio()
    async def test_pipeline_initializes_processed_flights(
        self,
        sample_extraction_list: FlightExtractionList,
    ) -> None:
        """Pipeline converts FlightExtraction to ProcessedFlight."""
        pipeline = FlightProcessingPipeline(processors=[])
        result = await pipeline.run(sample_extraction_list)

        for flight in result:
            assert flight.origin_id is None
            assert flight.destination_id is None
            assert flight.seats_available is None
            assert flight.seat_status is None

    @pytest.mark.asyncio()
    async def test_pipeline_runs_processors_sequentially(
        self,
        sample_extraction_list: FlightExtractionList,
    ) -> None:
        """Pipeline runs registered processors in order."""
        call_order: list[str] = []

        class ProcessorA:
            async def process_batch(
                self, flights: list[ProcessedFlight]
            ) -> list[ProcessedFlight]:
                call_order.append("A")
                return flights

        class ProcessorB:
            async def process_batch(
                self, flights: list[ProcessedFlight]
            ) -> list[ProcessedFlight]:
                call_order.append("B")
                return flights

        pipeline = FlightProcessingPipeline(processors=[ProcessorA(), ProcessorB()])
        await pipeline.run(sample_extraction_list)

        assert call_order == ["A", "B"]


class TestOCRService:
    """Tests for the OCRService orchestrator."""

    @pytest.mark.asyncio()
    async def test_process_document_creates_flight_models(
        self,
        mock_db_session: AsyncMock,
        sample_extraction_list: FlightExtractionList,
        sample_terminal_document: TerminalDocument,
    ) -> None:
        """OCRService creates Flight ORM objects from extractions."""
        mock_ocr_client = AsyncMock(spec=GeminiOCRClient)
        mock_ocr_client.extract.return_value = sample_extraction_list

        mock_pipeline = AsyncMock(spec=FlightProcessingPipeline)
        mock_pipeline.run.return_value = [
            ProcessedFlight(
                roll_call_time=datetime(2026, 3, 10, 14, 0, tzinfo=UTC),
                raw_seats="20F",
                raw_origin="Travis AFB",
                raw_destination="Ramstein AB",
            ),
            ProcessedFlight(
                roll_call_time=datetime(2026, 3, 11, 8, 30, tzinfo=UTC),
                raw_seats="TBD",
                raw_origin="Dover AFB",
                raw_destination="Incirlik AB",
            ),
        ]

        service = OCRService(
            db_session=mock_db_session,
            ocr_client=mock_ocr_client,
            pipeline=mock_pipeline,
        )

        await service.process_document(
            document=sample_terminal_document,
            raw_bytes=b"fake pdf bytes",
        )

        # Should have added 2 Flight objects
        assert mock_db_session.add.call_count == 2

        # Verify the Flight objects have correct terminal_doc_id
        for call in mock_db_session.add.call_args_list:
            flight = call.args[0]
            assert flight.terminal_doc_id == 42

    @pytest.mark.asyncio()
    async def test_process_document_commits(
        self,
        mock_db_session: AsyncMock,
        sample_extraction_list: FlightExtractionList,
        sample_terminal_document: TerminalDocument,
    ) -> None:
        """OCRService commits after processing."""
        mock_ocr_client = AsyncMock(spec=GeminiOCRClient)
        mock_ocr_client.extract.return_value = sample_extraction_list

        mock_pipeline = AsyncMock(spec=FlightProcessingPipeline)
        mock_pipeline.run.return_value = []

        service = OCRService(
            db_session=mock_db_session,
            ocr_client=mock_ocr_client,
            pipeline=mock_pipeline,
        )

        await service.process_document(
            document=sample_terminal_document,
            raw_bytes=b"fake pdf bytes",
        )

        mock_db_session.commit.assert_awaited_once()

    @pytest.mark.asyncio()
    async def test_process_document_handles_empty_extraction(
        self,
        mock_db_session: AsyncMock,
        sample_terminal_document: TerminalDocument,
    ) -> None:
        """OCRService handles documents with no flights."""
        mock_ocr_client = AsyncMock(spec=GeminiOCRClient)
        mock_ocr_client.extract.return_value = FlightExtractionList(flights=[])

        mock_pipeline = AsyncMock(spec=FlightProcessingPipeline)
        mock_pipeline.run.return_value = []

        service = OCRService(
            db_session=mock_db_session,
            ocr_client=mock_ocr_client,
            pipeline=mock_pipeline,
        )

        await service.process_document(
            document=sample_terminal_document,
            raw_bytes=b"fake pdf bytes",
        )

        mock_db_session.add.assert_not_called()
        mock_db_session.commit.assert_awaited_once()
