"""Shared custom exceptions for the SpaceATracker applications."""


class DocumentDownloadError(Exception):
    """Raised when a terminal document cannot be downloaded due to WAF or connection issues."""

    pass
