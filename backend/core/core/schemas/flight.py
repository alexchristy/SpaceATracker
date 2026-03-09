"""Pydantic schemas for flight extraction and processing."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from core.enums.seats import SeatStatus


class FlightExtraction(BaseModel):
    """Strictly the raw data extracted by the LLM."""

    roll_call_time: datetime
    raw_seats: str
    raw_origin: str
    raw_destination: str


class FlightExtractionList(BaseModel):
    """Container for a batch of flight extractions."""

    flights: list[FlightExtraction]


class ProcessedFlight(FlightExtraction):
    """The enriched flight data ready for database insertion."""

    origin_id: str | None = None
    destination_id: str | None = None
    seats_available: int | None = None
    seat_status: SeatStatus | None = None
    model_config = ConfigDict(from_attributes=True)
