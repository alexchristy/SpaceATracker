"""Service handling the periodic extraction of documents from known terminals."""

import hashlib
import logging
import mimetypes
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import magic
from core.models.location import MilitaryAirport
from core.models.terminal_document import TerminalDocument
from core.schemas.exceptions import DocumentDownloadError
from scraper.extraction.chain import ExtractionChain
from scraper.extraction.client import ExtractionClient
from scraper.extraction.strategies.amc_image_link import AMCImageLinkExtractor
from scraper.extraction.strategies.amc_text_link import AMCTextLinkExtractor
from sqlalchemy import select

if TYPE_CHECKING:
    from scraper.ocr.service import OCRService
    from scraper.storage.s3 import S3Client
    from sqlalchemy.ext.asyncio import AsyncSession


logger = logging.getLogger(__name__)


class ExtractionService:
    """Service handling the periodic extraction of documents from known terminals."""

    def __init__(
        self,
        db_session: AsyncSession,
        s3_client: S3Client,
        ocr_service: OCRService | None = None,
    ) -> None:
        """Initialize with a database session, S3 client, and optional OCR service."""
        self.db = db_session
        self.s3_client = s3_client
        self.ocr_service = ocr_service
        self.chain = ExtractionChain(
            strategies=[
                AMCTextLinkExtractor(),
                AMCImageLinkExtractor(),
            ]
        )

    async def run_extraction(self) -> None:
        """Execute the extraction workflow.

        1. Fetch all terminal URLs from DB.
        2. Download terminal HTML.
        3. Pass HTML through ExtractionChain.
        4. Log discovered document URLs.
        5. (Future) Download → hash → dedup → upload to MinIO → insert DB row.
        """
        logger.info("Starting Extraction Scraper Workflow...")

        # 1. Fetch terminals
        stmt = select(MilitaryAirport).where(MilitaryAirport.website_url.is_not(None))
        result = await self.db.execute(stmt)
        terminals = result.scalars().all()

        if not terminals:
            logger.warning("No terminals found with website URLs in the database.")
            return

        terminals_processed = 0
        terminals_failed = 0
        docs_discovered = 0
        docs_stored = 0
        docs_skipped = 0
        docs_failed = 0
        docs_stored_by_type = {
            "schedule_72hr": 0,
            "schedule_30day": 0,
            "rollcall": 0,
        }

        async with ExtractionClient() as client:
            for terminal in terminals:
                assert terminal.website_url is not None
                url = str(terminal.website_url)

                name_display = terminal.name or str(terminal.id)
                logger.debug("Processing terminal: %s (%s)", name_display, url)

                try:
                    html = await client.fetch_terminal_page(url)
                except Exception:
                    logger.exception("Failed to fetch HTML for %s", name_display)
                    terminals_failed += 1
                    continue

                terminals_processed += 1
                extraction_result = await self.chain.execute(html, terminal)

                # Log the extracted document URLs.
                if extraction_result.schedule_72hr_url:
                    logger.info(
                        "72hr schedule for %s: %s",
                        name_display,
                        extraction_result.schedule_72hr_url,
                    )
                if extraction_result.schedule_30day_url:
                    logger.info(
                        "30-day schedule for %s: %s",
                        name_display,
                        extraction_result.schedule_30day_url,
                    )
                if extraction_result.rollcall_url:
                    logger.info(
                        "Rollcall for %s: %s",
                        name_display,
                        extraction_result.rollcall_url,
                    )

                # Process each extracted document URL
                for doc_type, doc_url in [
                    ("schedule_72hr", extraction_result.schedule_72hr_url),
                    ("schedule_30day", extraction_result.schedule_30day_url),
                    ("rollcall", extraction_result.rollcall_url),
                ]:
                    if not doc_url:
                        continue

                    docs_discovered += 1

                    try:
                        # 1. Download
                        raw_bytes = await client.download_document(str(doc_url))

                        # 2. Hash & Type Detection
                        content_hash = hashlib.sha256(raw_bytes).hexdigest()
                        mime_type = magic.from_buffer(raw_bytes, mime=True)

                        # 3. Deduplication Check (Global)
                        stmt = (
                            select(TerminalDocument)
                            .where(TerminalDocument.content_hash == content_hash)
                            .limit(1)
                        )
                        existing_doc = (
                            await self.db.execute(stmt)
                        ).scalar_one_or_none()

                        if existing_doc:
                            logger.info(
                                "DUPLICATE HASH DETECTED: Skipping upload & insert for %s - %s. Hash %s already exists in DB (first seen at %s).",
                                name_display,
                                doc_type,
                                content_hash[:8],
                                existing_doc.scraped_at,
                            )
                            docs_skipped += 1
                            continue

                        # 4. Storage Key Generation
                        extension = mimetypes.guess_extension(mime_type) or ""
                        key = f"terminals/{terminal.id}/{doc_type}/{content_hash}{extension}"

                        # 5. Upload to SeaweedFS / S3
                        await self.s3_client.upload_file(key, raw_bytes)

                        # 6. Database Insert
                        new_doc = TerminalDocument(
                            terminal_id=str(terminal.id),
                            doc_type=doc_type,
                            url=str(doc_url),
                            content_hash=content_hash,
                            storage_key=key,
                            mime_type=mime_type,
                            scraped_at=datetime.now(UTC),
                        )
                        self.db.add(new_doc)
                        logger.info(
                            "Saved new %s for %s -> %s", doc_type, name_display, key
                        )
                        docs_stored += 1
                        docs_stored_by_type[doc_type] += 1

                        # 7. OCR Extraction
                        if self.ocr_service:
                            try:
                                await self.ocr_service.process_document(
                                    document=new_doc,
                                    raw_bytes=raw_bytes,
                                )
                            except Exception:
                                logger.exception(
                                    "OCR failed for %s - %s",
                                    name_display,
                                    doc_type,
                                )

                    except DocumentDownloadError as e:
                        # WAF block or known broken link. No need for a loud traceback.
                        logger.warning("%s - Skipping %s", e, doc_type)
                        docs_failed += 1
                    except Exception:
                        logger.exception(
                            "Failed to process %s document for %s",
                            doc_type,
                            name_display,
                        )
                        docs_failed += 1

        await self.db.commit()

        logger.info(
            "Extraction Complete. "
            "Terminals: %d processed, %d failed | "
            "Documents: %d discovered, %d stored as new (%s), %d skipped (unchanged), %d failed",
            terminals_processed,
            terminals_failed,
            docs_discovered,
            docs_stored,
            ", ".join(f"{v} {k}" for k, v in docs_stored_by_type.items() if v > 0)
            or "none",
            docs_skipped,
            docs_failed,
        )
