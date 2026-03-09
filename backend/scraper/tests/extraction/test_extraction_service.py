import hashlib
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from core.models.location import MilitaryAirport
from core.models.terminal_document import TerminalDocument
from core.schemas.extraction import ExtractionResult
from scraper.extraction.service import ExtractionService


@pytest.fixture
def mock_db_session():
    return AsyncMock()


@pytest.fixture
def mock_s3_client():
    client = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_extraction_service_global_deduplication(mock_db_session, mock_s3_client):
    """Test that a globally existing content hash skips S3 upload and DB insert."""
    service = ExtractionService(mock_db_session, mock_s3_client)

    # Mock terminal
    terminal = MilitaryAirport(
        id="test-terminal",
        name="Test Terminal",
        website_url="http://example.com/test",
    )

    # Mock ExtractionChain to return one document
    service.chain = AsyncMock()
    service.chain.execute.return_value = ExtractionResult(
        schedule_72hr_url="http://example.com/doc.pdf",
    )

    # Mock ExtractionClient
    mock_client_instance = AsyncMock()
    mock_client_instance.fetch_terminal_page.return_value = "<html></html>"
    # The document bytes
    test_bytes = b"test document content"
    mock_client_instance.download_document.return_value = test_bytes

    # Patch the context manager for ExtractionClient
    class MockClientContextManager:
        async def __aenter__(self):
            return mock_client_instance

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    # Mocking the discovery query (step 1) to return our terminal
    mock_result_terminals = MagicMock()
    mock_result_terminals.scalars().all.return_value = [terminal]

    # Mocking the deduplication query (step 3) to return an EXISTING document
    mock_result_existing = MagicMock()
    existing_doc = TerminalDocument(
        id=1,
        terminal_id="other-terminal",  # existing hash from a DIFFERENT terminal
        doc_type="schedule_30day",
        url="http://example.com/other.pdf",
        content_hash=hashlib.sha256(test_bytes).hexdigest(),
        storage_key="terminals/other-terminal/schedule_30day/hash.pdf",
        mime_type="application/pdf",
        scraped_at=datetime.now(UTC),
    )
    mock_result_existing.scalar_one_or_none.return_value = existing_doc

    # Set up the DB session execute to return the correct mock result based on the query
    async def mock_execute(stmt):
        stmt_str = str(stmt).lower()
        if "locations" in stmt_str:
            return mock_result_terminals
        if "terminal_documents" in stmt_str:
            return mock_result_existing
        return MagicMock()

    mock_db_session.execute.side_effect = mock_execute

    # Run extraction with patched client
    import scraper.extraction.service as m_service

    original_client = m_service.ExtractionClient
    m_service.ExtractionClient = lambda: MockClientContextManager()

    try:
        await service.run_extraction()

        # Verify deduplication branch was taken:
        # 1. NO s3 upload should have occurred
        mock_s3_client.upload_file.assert_not_called()

        # 2. NO new document should have been added to the session
        mock_db_session.add.assert_not_called()

    finally:
        # Restore original client
        m_service.ExtractionClient = original_client
