"""Strategy for extracting document links from text-based anchor tags."""

import logging
import re
from urllib.parse import urljoin

from core.schemas.extraction import ExtractionResult
from core.schemas.location import MilitaryAirportRead
from selectolax.parser import HTMLParser

logger = logging.getLogger(__name__)

# File extensions that indicate a downloadable document.
_DOC_EXTENSIONS = re.compile(r"\.(pdf|pptx|docx|xlsx)", re.IGNORECASE)

# Classification patterns applied to the *anchor text*.
_72HR_PATTERN = re.compile(r"72[\s\-_]*(hour|hrs|hr|h\b|h(?![a-z]))", re.IGNORECASE)
_30DAY_PATTERN = re.compile(r"30[\s\-]*(day)", re.IGNORECASE)
_ROLLCALL_PATTERN = re.compile(r"roll[\s\-]*call", re.IGNORECASE)


def _is_document_href(href: str) -> bool:
    """Return True if the href points to a document file or a LinkClick download."""
    return bool(_DOC_EXTENSIONS.search(href)) or "linkclick.aspx" in href.lower()


def _classify_text(text: str) -> str | None:
    """Classify anchor text into a document type key, or None if unrecognised."""
    if _72HR_PATTERN.search(text):
        return "schedule_72hr_url"
    if _30DAY_PATTERN.search(text):
        return "schedule_30day_url"
    if _ROLLCALL_PATTERN.search(text):
        return "rollcall_url"
    return None


class AMCTextLinkExtractor:
    """Finds document links in <a> tags by matching anchor text keywords.

    Targets pages where schedule/rollcall PDFs are linked via descriptive
    text such as "72-Hour Schedule" or "Roll Call Report".
    """

    async def extract_docs(
        self, html: str, terminal: MilitaryAirportRead
    ) -> ExtractionResult:
        """Extract document URLs by matching anchor text keywords."""
        tree = HTMLParser(html)
        base_url = str(terminal.website_url) if terminal.website_url else ""
        found: dict[str, str] = {}

        for a_tag in tree.css("a"):
            href = a_tag.attributes.get("href")
            if not href or not _is_document_href(href):
                continue

            text = a_tag.text(strip=True)
            if not text:
                continue

            doc_key = _classify_text(text)
            if doc_key and doc_key not in found:
                absolute_url = urljoin(base_url, href)
                found[doc_key] = absolute_url
                logger.debug(
                    "AMCTextLinkExtractor: %s matched '%s' for %s",
                    doc_key,
                    text[:60],
                    terminal.name,
                )

            if len(found) == 3:  # noqa: PLR2004
                break  # All three doc types found

        return ExtractionResult(**found)
