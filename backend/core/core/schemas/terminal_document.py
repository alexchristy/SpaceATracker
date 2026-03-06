"""Pydantic schemas for terminal document validation and serialization."""

from datetime import datetime

from pydantic import AnyUrl, BaseModel, ConfigDict

from core.enums.document import DocumentType


class TerminalDocumentCreate(BaseModel):
    """Schema for creating a new terminal document record."""

    terminal_id: str
    doc_type: DocumentType
    url: AnyUrl
    content_hash: str
    storage_key: str
    mime_type: str
    scraped_at: datetime


class TerminalDocumentRead(TerminalDocumentCreate):
    """Schema for reading a terminal document record from the database."""

    id: int
    model_config = ConfigDict(from_attributes=True)
