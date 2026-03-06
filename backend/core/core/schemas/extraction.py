"""Pydantic schemas for extraction pipeline results."""

from pydantic import AnyUrl, BaseModel


class ExtractionResult(BaseModel):
    """Output of the extraction chain — one optional URL per document type."""

    schedule_72hr_url: AnyUrl | None = None
    schedule_30day_url: AnyUrl | None = None
    rollcall_url: AnyUrl | None = None
