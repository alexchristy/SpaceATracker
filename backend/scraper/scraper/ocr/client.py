"""Async wrapper around the Gemini API for OCR extraction."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.schemas.flight import FlightExtractionList
from google import genai
from google.genai import types

from scraper.ocr.prompt import SYSTEM_INSTRUCTION

if TYPE_CHECKING:
    from google.genai import Client

logger = logging.getLogger(__name__)

_MODEL = "gemini-2.0-flash"


class GeminiOCRClient:
    """Extracts flight data from documents using Gemini."""

    def __init__(self, genai_client: Client) -> None:
        """Initialize with a google-genai Client instance.

        Args:
            genai_client: An authenticated google.genai.Client.
        """
        self._client = genai_client

    @classmethod
    def from_api_key(cls, api_key: str) -> GeminiOCRClient:
        """Create a client from an API key.

        Args:
            api_key: The Gemini API key.

        Returns:
            A configured GeminiOCRClient.
        """
        client = genai.Client(api_key=api_key)
        return cls(genai_client=client)

    async def extract(
        self,
        file_bytes: bytes,
        mime_type: str,
    ) -> FlightExtractionList:
        """Extract flight data from raw document bytes.

        Args:
            file_bytes: The raw file content.
            mime_type: The MIME type of the file.

        Returns:
            A validated FlightExtractionList.
        """
        inline_data = types.Part.from_bytes(
            data=file_bytes,
            mime_type=mime_type,
        )

        response = await self._client.aio.models.generate_content(
            model=_MODEL,
            contents=[inline_data],
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=FlightExtractionList,
            ),
        )

        logger.info(
            "Gemini extraction complete: %d flights",
            len(response.parsed.flights),
        )
        return response.parsed
