"""Async S3 / SeaweedFS Client Wrapper."""

import logging
from typing import TYPE_CHECKING

import aiobotocore.session
from scraper.core.config import settings

if TYPE_CHECKING:
    from types import TracebackType


logger = logging.getLogger(__name__)


class S3Client:
    """Async wrapper for uploading files to S3-compatible object storage."""

    def __init__(self) -> None:
        """Initialize connection parameters from settings."""
        self.endpoint_url = settings.S3_ENDPOINT_URL
        self.access_key = settings.S3_ACCESS_KEY
        self.secret_key = settings.S3_SECRET_KEY
        self.bucket = settings.S3_BUCKET_NAME
        self.session = aiobotocore.session.get_session()
        self.client = None

    async def __aenter__(self) -> S3Client:
        """Enter the async context manager and instantiate the client."""
        # The create_client method returns an async context manager itself,
        # so we need to enter *that* context manager to give the underlying
        # aiobotocore client to our custom wrapper.
        self._client_cm = self.session.create_client(
            "s3",
            endpoint_url=self.endpoint_url,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        )
        self.client = await self._client_cm.__aenter__()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the async context manager and close the client."""
        if self._client_cm is not None:
            await self._client_cm.__aexit__(exc_type, exc_val, exc_tb)
            self._client_cm = None
            self.client = None

    async def upload_file(self, key: str, data: bytes) -> None:
        """Upload raw bytes to S3.

        Args:
            key: The S3 object key (e.g. terminals/foo/doc.pdf).
            data: The raw file bytes.
        """
        if self.client is None:
            raise RuntimeError("S3Client must be used as an async context manager")

        logger.info("Uploading %d bytes to s3://%s/%s", len(data), self.bucket, key)
        await self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
        )
