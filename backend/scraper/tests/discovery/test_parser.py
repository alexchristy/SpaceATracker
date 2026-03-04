import csv
import pathlib
from typing import TYPE_CHECKING

import pytest
from scraper.discovery.parser import DirectoryParser

if TYPE_CHECKING:
    from core.schemas.location import MilitaryAirportCreate

from core.schemas.location import generate_location_id


def get_asset_dirs() -> list[pathlib.Path]:
    """Finds all subdirectories in the assets/ folder that contain both an HTML and CSV file."""
    asset_base = pathlib.Path(__file__).parent / "assets"
    dirs = []
    if asset_base.exists():
        dirs.extend(
            d
            for d in asset_base.iterdir()
            if d.is_dir()
            and next(d.glob("*.html"), None)
            and next(d.glob("*.csv"), None)
        )
    return dirs


@pytest.fixture(scope="module", params=get_asset_dirs(), ids=lambda d: d.name)
def asset_dir(request: pytest.FixtureRequest) -> pathlib.Path:
    """Parametrized fixture yielding each valid asset subdirectory."""
    return request.param


@pytest.fixture(scope="module")
def amc_directory_html(asset_dir: pathlib.Path) -> str:
    """Fixture providing the raw AMC Space-A directory HTML from the parameterized directory."""
    html_file = next(iter(asset_dir.glob("*.html")))
    with open(html_file, encoding="utf-8") as f:
        return f.read()


@pytest.fixture(scope="module")
def amc_terminals_csv(asset_dir: pathlib.Path) -> list[dict[str, str]]:
    """Fixture providing the manually verified CSV rows from the parameterized directory."""
    csv_file = next(iter(asset_dir.glob("*.csv")))
    with open(csv_file, encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        return list(reader)


@pytest.fixture(scope="module")
def extracted_terminals(amc_directory_html: str) -> list[MilitaryAirportCreate]:
    """Fixture that runs the parser once to share the output across multiple test cases."""
    parser = DirectoryParser(amc_directory_html)
    return list(parser.extract_terminals())


def _normalize_test_url(url: str) -> str:
    """Normalizes URLs to compare manual CSV entries against actual HTML links."""
    return (
        url.lower()
        .replace("http://", "https://")
        .rstrip("/")
        .removesuffix(".html")
        .removesuffix(".aspx")
    )


def test_parser_extracts_all_terminal_locations(
    extracted_terminals: list[MilitaryAirportCreate],
    amc_terminals_csv: list[dict[str, str]],
) -> None:
    """Verifies that the parser finds every single terminal location listed in the CSV."""
    extracted_ids = {t.id for t in extracted_terminals}
    missing_terminals = []

    for row in amc_terminals_csv:
        expected_location = row["Location"].strip()
        expected_id = generate_location_id(expected_location)

        if expected_id not in extracted_ids:
            missing_terminals.append(expected_location)

    assert not missing_terminals, (
        f"Parser missed {len(missing_terminals)} terminals from the CSV location column: {missing_terminals}"
    )


def test_parser_extracts_correct_raw_locations(
    extracted_terminals: list[MilitaryAirportCreate],
    amc_terminals_csv: list[dict[str, str]],
) -> None:
    """Verifies that the parser extracts the raw location text correctly."""
    extracted_dict = {t.id: t for t in extracted_terminals}

    for row in amc_terminals_csv:
        expected_location = row["Location"].strip()
        expected_id = generate_location_id(expected_location)

        extracted_terminal = extracted_dict.get(expected_id)
        if not extracted_terminal:
            continue

        assert extracted_terminal.raw_location == expected_location, (
            f"Expected raw_location '{expected_location}', got '{extracted_terminal.raw_location}'"
        )


def test_parser_extracts_correct_terminal_names(
    extracted_terminals: list[MilitaryAirportCreate],
    amc_terminals_csv: list[dict[str, str]],
) -> None:
    """Verifies that the parser extracts the correct terminal name from the link text, or None if absent."""
    extracted_dict = {t.id: t for t in extracted_terminals}

    for row in amc_terminals_csv:
        expected_location = row["Location"].strip()
        expected_name = row["Name"].strip() or None
        expected_id = generate_location_id(expected_location)

        extracted_terminal = extracted_dict.get(expected_id)
        if not extracted_terminal:
            continue

        assert extracted_terminal.name == expected_name, (
            f"Expected name '{expected_name}' for {expected_location}, got '{extracted_terminal.name}'"
        )


def test_parser_extracts_correct_webpage_urls(
    extracted_terminals: list[MilitaryAirportCreate],
    amc_terminals_csv: list[dict[str, str]],
) -> None:
    """Verifies that the parser extracts the correct website URL for each terminal, or None if it doesn't exist."""
    extracted_dict = {t.id: t for t in extracted_terminals}

    for row in amc_terminals_csv:
        expected_location = row["Location"].strip()
        expected_url = row["URL"].strip()
        expected_id = generate_location_id(expected_location)

        extracted_terminal = extracted_dict.get(expected_id)
        if not extracted_terminal:
            continue

        if expected_url:
            assert extracted_terminal.website_url is not None, (
                f"Expected URL {expected_url} for {expected_location} but got None"
            )
            norm_extracted = _normalize_test_url(str(extracted_terminal.website_url))
            norm_expected = _normalize_test_url(expected_url)

            assert norm_extracted.startswith(norm_expected) or norm_expected.startswith(
                norm_extracted
            ), (
                f"Mismatched URL for {expected_location}. Expected {expected_url}, got {extracted_terminal.website_url}"
            )
        else:
            assert extracted_terminal.website_url is None, (
                f"Expected None URL for {expected_location} but got {extracted_terminal.website_url}"
            )


def test_parser_generates_deterministic_ids(
    extracted_terminals: list[MilitaryAirportCreate],
) -> None:
    """Verifies that each terminal has a non-empty, lowercase, hyphenated ID."""
    for terminal in extracted_terminals:
        assert terminal.id, f"Terminal has empty ID: {terminal}"
        assert terminal.id == terminal.id.lower(), (
            f"ID should be lowercase: {terminal.id}"
        )
        assert " " not in terminal.id, f"ID should not contain spaces: {terminal.id}"


def test_parser_extracts_correct_terminal_group(
    extracted_terminals: list[MilitaryAirportCreate],
    amc_terminals_csv: list[dict[str, str]],
) -> None:
    """Verifies that the parser extracts the correct terminal group (e.g. 'EUCOM Terminals') from the accordion."""
    extracted_dict = {t.id: t for t in extracted_terminals}

    for row in amc_terminals_csv:
        expected_location = row["Location"].strip()
        expected_group = row["Group"].strip()
        expected_id = generate_location_id(expected_location)

        extracted_terminal = extracted_dict.get(expected_id)
        if not extracted_terminal:
            continue

        assert extracted_terminal.terminal_group == expected_group, (
            f"Expected group {expected_group} for {expected_location}, got {extracted_terminal.terminal_group}"
        )
