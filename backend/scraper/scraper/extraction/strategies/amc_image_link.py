"""Strategy for extracting document links from image-wrapped anchor tags."""

import logging
import re
from urllib.parse import urljoin

from core.schemas.extraction import ExtractionResult
from core.schemas.location import MilitaryAirportRead
from selectolax.parser import HTMLParser

logger = logging.getLogger(__name__)

# File extensions that indicate a downloadable document.
_DOC_EXTENSIONS = re.compile(r"\.(pdf|pptx|docx|xlsx)", re.IGNORECASE)

# Classification patterns — applied to img alt/title *or* the href path.
_72HR_PATTERN = re.compile(r"72[\s\-_]*(hour|hrs|hr|h\b|h(?![a-z]))", re.IGNORECASE)
_30DAY_PATTERN = re.compile(r"30[\s\-]*(day)|30[\s_\-]*day", re.IGNORECASE)
_ROLLCALL_PATTERN = re.compile(r"roll[\s\-]*call", re.IGNORECASE)


def _is_document_href(href: str) -> bool:
    """Return True if the href points to a document file or a LinkClick download."""
    return bool(_DOC_EXTENSIONS.search(href)) or "linkclick.aspx" in href.lower()


def _classify(text: str) -> str | None:
    """Classify text into a document type key, or None if unrecognised."""
    if _72HR_PATTERN.search(text):
        return "schedule_72hr_url"
    if _30DAY_PATTERN.search(text):
        return "schedule_30day_url"
    if _ROLLCALL_PATTERN.search(text):
        return "rollcall_url"
    return None


class AMCImageLinkExtractor:
    """Finds document links in <a> tags that wrap <img> children.

    Many AMC terminal pages use clickable banner images (e.g. a blue
    "72-Hour Schedule" thumbnail) that link to the actual PDF. This strategy
    classifies the link by examining the <img> alt/title attributes first,
    falling back to keywords in the href path.
    """

    async def extract_docs(
        self, html: str, terminal: MilitaryAirportRead
    ) -> ExtractionResult:
        """Extract document URLs from image-wrapped links."""
        tree = HTMLParser(html)
        base_url = str(terminal.website_url) if terminal.website_url else ""
        found: dict[str, str] = {}

        for a_tag in tree.css("a"):
            href = a_tag.attributes.get("href")
            if not href or not _is_document_href(href):
                continue

            # Only consider links that wrap an <img> child.
            img = a_tag.css_first("img")
            if img is None:
                continue

            # Try to classify from the image alt or title attribute.
            doc_key: str | None = None
            alt = img.attributes.get("alt") or ""
            title = img.attributes.get("title") or ""
            src = img.attributes.get("src") or ""
            candidate_text = f"{alt} {title}".strip()
            if candidate_text:
                doc_key = _classify(candidate_text)

            # Fallback: classify from the img src attribute.
            if doc_key is None and src:
                doc_key = _classify(src)

            # Fallback: classify from the href path itself.
            if doc_key is None:
                doc_key = _classify(href)

            if doc_key and doc_key not in found:
                absolute_url = urljoin(base_url, href)
                found[doc_key] = absolute_url
                logger.debug(
                    "AMCImageLinkExtractor: %s via img alt='%s' for %s",
                    doc_key,
                    (alt or "")[:60],
                    terminal.name,
                )

            if len(found) == 3:  # noqa: PLR2004
                break  # All three doc types found

        return ExtractionResult(**found)
