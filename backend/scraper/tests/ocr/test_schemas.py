"""Tests for flight extraction schemas."""

from datetime import UTC, datetime

from core.enums.seats import SeatStatus
from core.schemas.flight import FlightExtraction, FlightExtractionList, ProcessedFlight


class TestFlightExtraction:
    """Tests for the FlightExtraction schema."""

    def test_valid_construction(self):
        """FlightExtraction accepts valid raw data."""
        flight = FlightExtraction(
            roll_call_time=datetime(2026, 3, 10, 14, 0, tzinfo=UTC),
            raw_seats="20F",
            raw_origin="Travis AFB",
            raw_destination="Ramstein AB",
        )
        assert flight.raw_origin == "Travis AFB"
        assert flight.raw_destination == "Ramstein AB"
        assert flight.raw_seats == "20F"

    def test_roll_call_time_is_datetime(self):
        """roll_call_time must be a datetime."""
        flight = FlightExtraction(
            roll_call_time=datetime(2026, 3, 10, 14, 0, tzinfo=UTC),
            raw_seats="TBD",
            raw_origin="Dover AFB",
            raw_destination="Incirlik AB",
        )
        assert isinstance(flight.roll_call_time, datetime)


class TestFlightExtractionList:
    """Tests for the FlightExtractionList schema."""

    def test_holds_list_of_extractions(self):
        """FlightExtractionList wraps a list of FlightExtraction."""
        extraction = FlightExtraction(
            roll_call_time=datetime(2026, 3, 10, 14, 0, tzinfo=UTC),
            raw_seats="10T",
            raw_origin="McGuire AFB",
            raw_destination="Lajes Field",
        )
        result = FlightExtractionList(flights=[extraction])
        assert len(result.flights) == 1
        assert result.flights[0].raw_origin == "McGuire AFB"

    def test_empty_list(self):
        """FlightExtractionList accepts an empty list."""
        result = FlightExtractionList(flights=[])
        assert result.flights == []


class TestProcessedFlight:
    """Tests for the ProcessedFlight schema."""

    def test_inherits_extraction_fields(self):
        """ProcessedFlight includes all FlightExtraction fields."""
        processed = ProcessedFlight(
            roll_call_time=datetime(2026, 3, 10, 14, 0, tzinfo=UTC),
            raw_seats="5F",
            raw_origin="Travis AFB",
            raw_destination="Hickam AFB",
        )
        assert processed.raw_origin == "Travis AFB"
        assert processed.raw_seats == "5F"

    def test_enrichment_fields_default_none(self):
        """Enrichment fields default to None."""
        processed = ProcessedFlight(
            roll_call_time=datetime(2026, 3, 10, 14, 0, tzinfo=UTC),
            raw_seats="5F",
            raw_origin="Travis AFB",
            raw_destination="Hickam AFB",
        )
        assert processed.origin_id is None
        assert processed.destination_id is None
        assert processed.seats_available is None
        assert processed.seat_status is None

    def test_enrichment_fields_accept_values(self):
        """ProcessedFlight accepts enriched values."""
        processed = ProcessedFlight(
            roll_call_time=datetime(2026, 3, 10, 14, 0, tzinfo=UTC),
            raw_seats="5F",
            raw_origin="Travis AFB",
            raw_destination="Hickam AFB",
            origin_id="travis-afb",
            destination_id="hickam-afb",
            seats_available=5,
            seat_status=SeatStatus.FIRM,
        )
        assert processed.origin_id == "travis-afb"
        assert processed.seats_available == 5
        assert processed.seat_status == SeatStatus.FIRM

    def test_from_attributes_enabled(self):
        """ProcessedFlight has from_attributes=True."""
        assert ProcessedFlight.model_config.get("from_attributes") is True
