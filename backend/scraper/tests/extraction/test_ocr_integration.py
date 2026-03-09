"""Test that ExtractionService calls OCRService after storing a new document."""

import hashlib
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from core.models.location import MilitaryAirport
from core.schemas.extraction import ExtractionResult
from scraper.extraction.service import ExtractionService


@pytest.fixture()
def mock_db_session() -> AsyncMock:
    """Provide a mocked async database session."""
    session = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture()
def mock_s3_client() -> AsyncMock:
    """Provide a mocked S3 client."""
    return AsyncMock()


@pytest.fixture()
def mock_ocr_service() -> AsyncMock:
    """Provide a mocked OCR service."""
    return AsyncMock()


@pytest.mark.asyncio()
async def test_extraction_calls_ocr_after_new_document(
    mock_db_session: AsyncMock,
    mock_s3_client: AsyncMock,
    mock_ocr_service: AsyncMock,
) -> None:
    """After inserting a new document, OCRService.process_document is called."""
    service = ExtractionService(
        mock_db_session,
        mock_s3_client,
        ocr_service=mock_ocr_service,
    )

    terminal = MilitaryAirport(
        id="test-terminal",
        name="Test Terminal",
        website_url="http://example.com/test",
    )

    service.chain = AsyncMock()
    service.chain.execute.return_value = ExtractionResult(
        schedule_72hr_url="http://example.com/doc.pdf",
    )

    mock_client_instance = AsyncMock()
    mock_client_instance.fetch_terminal_page.return_value = "<html></html>"
    test_bytes = b"new document content"
    mock_client_instance.download_document.return_value = test_bytes

    class MockClientContextManager:
        async def __aenter__(self) -> AsyncMock:
            return mock_client_instance

        async def __aexit__(
            self,
            exc_type: type | None,
            exc_val: BaseException | None,
            exc_tb: object,
        ) -> None:
            pass

    # Terminal query returns our terminal
    mock_result_terminals = MagicMock()
    mock_result_terminals.scalars().all.return_value = [terminal]

    # Dedup query returns NO existing doc (new document)
    mock_result_dedup = MagicMock()
    mock_result_dedup.scalar_one_or_none.return_value = None

    async def mock_execute(stmt: object) -> MagicMock:
        stmt_str = str(stmt).lower()
        if "locations" in stmt_str:
            return mock_result_terminals
        if "terminal_documents" in stmt_str:
            return mock_result_dedup
        return MagicMock()

    mock_db_session.execute.side_effect = mock_execute

    import scraper.extraction.service as m_service

    original_client = m_service.ExtractionClient
    m_service.ExtractionClient = lambda: MockClientContextManager()

    try:
        with patch("scraper.extraction.service.magic") as mock_magic:
            mock_magic.from_buffer.return_value = "application/pdf"
            await service.run_extraction()

        # OCRService should have been called with the new doc and bytes
        mock_ocr_service.process_document.assert_awaited_once()
        call_kwargs = mock_ocr_service.process_document.call_args
        assert call_kwargs.kwargs["raw_bytes"] == test_bytes

    finally:
        m_service.ExtractionClient = original_client


@pytest.mark.asyncio()
async def test_extraction_skips_ocr_when_no_service(
    mock_db_session: AsyncMock,
    mock_s3_client: AsyncMock,
) -> None:
    """ExtractionService works without OCRService (backward compatible)."""
    service = ExtractionService(mock_db_session, mock_s3_client)

    terminal = MilitaryAirport(
        id="test-terminal",
        name="Test Terminal",
        website_url="http://example.com/test",
    )

    service.chain = AsyncMock()
    service.chain.execute.return_value = ExtractionResult(
        schedule_72hr_url="http://example.com/doc.pdf",
    )

    mock_client_instance = AsyncMock()
    mock_client_instance.fetch_terminal_page.return_value = "<html></html>"
    mock_client_instance.download_document.return_value = b"content"

    class MockClientContextManager:
        async def __aenter__(self) -> AsyncMock:
            return mock_client_instance

        async def __aexit__(
            self,
            exc_type: type | None,
            exc_val: BaseException | None,
            exc_tb: object,
        ) -> None:
            pass

    mock_result_terminals = MagicMock()
    mock_result_terminals.scalars().all.return_value = [terminal]

    mock_result_dedup = MagicMock()
    mock_result_dedup.scalar_one_or_none.return_value = None

    async def mock_execute(stmt: object) -> MagicMock:
        stmt_str = str(stmt).lower()
        if "locations" in stmt_str:
            return mock_result_terminals
        if "terminal_documents" in stmt_str:
            return mock_result_dedup
        return MagicMock()

    mock_db_session.execute.side_effect = mock_execute

    import scraper.extraction.service as m_service

    original_client = m_service.ExtractionClient
    m_service.ExtractionClient = lambda: MockClientContextManager()

    try:
        with patch("scraper.extraction.service.magic") as mock_magic:
            mock_magic.from_buffer.return_value = "application/pdf"
            # Should not raise even without ocr_service
            await service.run_extraction()

    finally:
        m_service.ExtractionClient = original_client
