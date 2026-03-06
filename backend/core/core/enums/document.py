"""Document type classification for terminal documents."""

from enum import StrEnum


class DocumentType(StrEnum):
    """Type of document scraped from a terminal webpage."""

    SCHEDULE_72HR = "schedule_72hr"
    SCHEDULE_30DAY = "schedule_30day"
    ROLLCALL = "rollcall"
