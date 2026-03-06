"""Data-driven integration tests for the extraction chain.

Tests the link extraction stage only (pure parsing, no DB, no downloads).
Auto-discovers snapshot subdirectories in the assets/ folder so adding a
new snapshot requires zero test code changes.
"""

import csv
import pathlib
from urllib.parse import unquote

import pytest
from core.schemas.extraction import ExtractionResult
from core.schemas.location import MilitaryAirportRead
from scraper.extraction.chain import ExtractionChain
from scraper.extraction.strategies.amc_image_link import AMCImageLinkExtractor
from scraper.extraction.strategies.amc_text_link import AMCTextLinkExtractor

ASSETS_DIR = pathlib.Path(__file__).parent / "assets"


# ---------------------------------------------------------------------------
# Snapshot discovery
# ---------------------------------------------------------------------------


def _discover_snapshots() -> list[tuple[pathlib.Path, pathlib.Path]]:
    """Return (csv_path, snapshot_dir) for every date subdirectory."""
    snapshots = []
    for child in sorted(ASSETS_DIR.iterdir()):
        if not child.is_dir():
            continue
        csvs = list(child.glob("terminal_docs_*.csv"))
        if csvs:
            snapshots.append((csvs[0], child))
    return snapshots


def _load_csv_rows(csv_path: pathlib.Path) -> list[dict[str, str]]:
    """Load all rows from a semicolon-delimited CSV."""
    with open(csv_path, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=";"))


def _normalize_url(url: str) -> str:
    """URL-decode, lowercase, and normalize protocol for comparison."""
    norm = unquote(url).lower().strip()
    if norm.startswith("https://"):
        norm = "http://" + norm[8:]
    return norm


# ---------------------------------------------------------------------------
# Test case builders
# ---------------------------------------------------------------------------

_SNAPSHOTS = _discover_snapshots()


def _build_test_cases(
    *, require_any_doc: bool = False, require_all_empty: bool = False
) -> list[tuple[str, pathlib.Path, dict[str, str]]]:
    """Build parametrized test case tuples from all discovered snapshots.

    Returns list of (test_id, snapshot_dir, csv_row).
    """
    cases = []
    for csv_path, snapshot_dir in _SNAPSHOTS:
        rows = _load_csv_rows(csv_path)
        for row in rows:
            has_72hr = bool(row.get("72_Hr_Schedule", "").strip())
            has_30day = bool(row.get("30_Day_Schedule", "").strip())
            has_rollcall = bool(row.get("Rollcall", "").strip())
            has_any = has_72hr or has_30day or has_rollcall
            all_empty = not has_any

            if require_any_doc and not has_any:
                continue
            if require_all_empty and not all_empty:
                continue

            test_id = f"{snapshot_dir.name}/{row['File']}"
            cases.append((test_id, snapshot_dir, row))
    return cases


def _build_field_cases(
    field: str,
) -> list[tuple[str, pathlib.Path, dict[str, str]]]:
    """Build test cases for rows that have a non-empty value for the given field."""
    cases = []
    for csv_path, snapshot_dir in _SNAPSHOTS:
        rows = _load_csv_rows(csv_path)
        for row in rows:
            if row.get(field, "").strip():
                test_id = f"{snapshot_dir.name}/{row['File']}"
                cases.append((test_id, snapshot_dir, row))
    return cases


async def _run_chain(html_path: pathlib.Path, source_url: str) -> ExtractionResult:
    """Run the extraction chain against a single HTML file."""
    html = html_path.read_text(encoding="utf-8")

    terminal = MilitaryAirportRead(
        id="test-terminal",
        name="Test Terminal",
        website_url=source_url,
    )

    chain = ExtractionChain(
        strategies=[
            AMCTextLinkExtractor(),
            AMCImageLinkExtractor(),
        ]
    )
    return await chain.execute(html, terminal)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

_empty_cases = _build_test_cases(require_all_empty=True)
_72hr_cases = _build_field_cases("72_Hr_Schedule")
_30day_cases = _build_field_cases("30_Day_Schedule")
_rollcall_cases = _build_field_cases("Rollcall")


@pytest.mark.parametrize(
    ("test_id", "snapshot_dir", "row"),
    _empty_cases,
    ids=[c[0] for c in _empty_cases],
)
async def test_no_docs_returns_empty(
    test_id: str,
    snapshot_dir: pathlib.Path,
    row: dict[str, str],
) -> None:
    """Terminals with no doc links should produce an empty ExtractionResult."""
    html_path = snapshot_dir / row["File"]
    result = await _run_chain(html_path, row["Source_URL"])

    assert result.schedule_72hr_url is None, (
        f"{test_id}: Expected no 72hr URL, got {result.schedule_72hr_url}"
    )
    assert result.schedule_30day_url is None, (
        f"{test_id}: Expected no 30day URL, got {result.schedule_30day_url}"
    )
    assert result.rollcall_url is None, (
        f"{test_id}: Expected no rollcall URL, got {result.rollcall_url}"
    )


@pytest.mark.parametrize(
    ("test_id", "snapshot_dir", "row"),
    _72hr_cases,
    ids=[c[0] for c in _72hr_cases],
)
async def test_72hr_schedule(
    test_id: str,
    snapshot_dir: pathlib.Path,
    row: dict[str, str],
) -> None:
    """Terminals with a 72hr schedule link should extract the correct URL."""
    html_path = snapshot_dir / row["File"]
    result = await _run_chain(html_path, row["Source_URL"])

    expected = row["72_Hr_Schedule"].strip()
    assert result.schedule_72hr_url is not None, (
        f"{test_id}: Expected 72hr URL but got None"
    )
    assert _normalize_url(str(result.schedule_72hr_url)) == _normalize_url(expected), (
        f"{test_id}: 72hr URL mismatch.\n"
        f"  Expected: {expected}\n"
        f"  Got:      {result.schedule_72hr_url}"
    )


@pytest.mark.parametrize(
    ("test_id", "snapshot_dir", "row"),
    _30day_cases,
    ids=[c[0] for c in _30day_cases],
)
async def test_30day_schedule(
    test_id: str,
    snapshot_dir: pathlib.Path,
    row: dict[str, str],
) -> None:
    """Terminals with a 30-day schedule link should extract the correct URL."""
    html_path = snapshot_dir / row["File"]
    result = await _run_chain(html_path, row["Source_URL"])

    expected = row["30_Day_Schedule"].strip()
    assert result.schedule_30day_url is not None, (
        f"{test_id}: Expected 30day URL but got None"
    )
    assert _normalize_url(str(result.schedule_30day_url)) == _normalize_url(expected), (
        f"{test_id}: 30day URL mismatch.\n"
        f"  Expected: {expected}\n"
        f"  Got:      {result.schedule_30day_url}"
    )


@pytest.mark.parametrize(
    ("test_id", "snapshot_dir", "row"),
    _rollcall_cases,
    ids=[c[0] for c in _rollcall_cases],
)
async def test_rollcall(
    test_id: str,
    snapshot_dir: pathlib.Path,
    row: dict[str, str],
) -> None:
    """Terminals with a rollcall link should extract the correct URL."""
    html_path = snapshot_dir / row["File"]
    result = await _run_chain(html_path, row["Source_URL"])

    expected = row["Rollcall"].strip()
    assert result.rollcall_url is not None, (
        f"{test_id}: Expected rollcall URL but got None"
    )
    assert _normalize_url(str(result.rollcall_url)) == _normalize_url(expected), (
        f"{test_id}: Rollcall URL mismatch.\n"
        f"  Expected: {expected}\n"
        f"  Got:      {result.rollcall_url}"
    )


async def test_strategy_coverage() -> None:
    """Each registered strategy should contribute at least one extraction."""
    strategies = [AMCTextLinkExtractor(), AMCImageLinkExtractor()]
    strategy_hits: dict[str, int] = {s.__class__.__name__: 0 for s in strategies}

    for csv_path, snapshot_dir in _SNAPSHOTS:
        rows = _load_csv_rows(csv_path)
        for row in rows:
            has_any = any(
                row.get(col, "").strip()
                for col in ("72_Hr_Schedule", "30_Day_Schedule", "Rollcall")
            )
            if not has_any:
                continue

            html_path = snapshot_dir / row["File"]
            html = html_path.read_text(encoding="utf-8")
            terminal = MilitaryAirportRead(
                id="test-terminal",
                name="Test Terminal",
                website_url=row["Source_URL"],
            )

            for strategy in strategies:
                result = await strategy.extract_docs(html, terminal)
                if any(
                    getattr(result, f) is not None
                    for f in (
                        "schedule_72hr_url",
                        "schedule_30day_url",
                        "rollcall_url",
                    )
                ):
                    strategy_hits[strategy.__class__.__name__] += 1

    for name, count in strategy_hits.items():
        assert count > 0, f"Strategy {name} never contributed any extractions"
