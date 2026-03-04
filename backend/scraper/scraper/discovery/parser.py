import html
import logging
from typing import TYPE_CHECKING

from core.enums.location import LocationType
from core.schemas.location import MilitaryAirportCreate, generate_location_id
from selectolax.parser import HTMLParser

if TYPE_CHECKING:
    from collections.abc import Iterator

logger = logging.getLogger(__name__)


class DirectoryParser:
    """Parses the main AMC Space-A directory HTML to find Terminal links."""

    def __init__(self, raw_html: str) -> None:
        self.tree = HTMLParser(raw_html)

    def extract_terminals(self) -> Iterator[MilitaryAirportCreate]:
        """Yields Pydantic validation models for MilitaryAirports found on the page.

        This dynamically searches for accordion list items that contain the terminals.
        Some terminals have links inside an embedded encoded HTML table,
        and some terminals only have names and no active website (like Clark AB).
        """
        items = self.tree.css("li.af3AccordionMenuListItem")
        seen_titles = set()
        current_group = None

        for item in items:
            # The parent accordion title usually precedes the terminal items
            root_node = item.css_first(".af3AccordionRootNode .menu-item-title")
            if root_node:
                current_group = " ".join(
                    root_node.text(deep=True, separator=" ").strip().split()
                )

            html_section = item.css_first("div.htmlSection")
            if not html_section:
                continue

            header_node = item.css_first(".af3MenuLinkHeader")
            if not header_node:
                continue

            raw_title = header_node.text(deep=True, separator=" ").strip()
            clean_name = " ".join(raw_title.split())

            if not clean_name or clean_name in seen_titles:
                continue

            seen_titles.add(clean_name)

            data_html = html_section.attributes.get("data-html", "")
            full_href = None
            terminal_name = None

            if data_html:
                # The table is HTML encoded inside the data attribute
                decoded_html = html.unescape(data_html)
                inner_tree = HTMLParser(decoded_html)

                for link in inner_tree.css("a"):
                    raw_href = link.attributes.get("href", "")

                    # Skip empty tags and mailto emails
                    if not raw_href or raw_href.startswith("mailto:"):
                        continue

                    link_text = link.text(strip=True)

                    # Skip links with no visible text (invisible layout links)
                    if not link_text:
                        continue

                    # Always grab the first valid href for the URL
                    if full_href is None:
                        full_href = raw_href
                        if full_href.startswith("/"):
                            full_href = f"https://www.amc.af.mil{full_href}"

                    # Only use link text as the terminal name if it's a
                    # human-readable name (not a URL, not a fragment)
                    if (
                        terminal_name is None
                        and len(link_text) >= 3
                        and not link_text.startswith(("http://", "https://", "www."))
                    ):
                        terminal_name = " ".join(link_text.split())

            terminal_id = generate_location_id(clean_name)

            try:
                yield MilitaryAirportCreate(
                    id=terminal_id,
                    name=terminal_name,
                    raw_location=clean_name,
                    location_type=LocationType.MILITARY_AIRPORT,
                    website_url=full_href,
                    terminal_group=current_group,
                )
            except Exception as e:
                logger.warning(
                    "Failed to validate terminal %s - %s: %s", clean_name, full_href, e
                )
