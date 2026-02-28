from core.enums.location import LocationType

from .base import Base
from .flight import Flight, SeatStatus
from .location import Location, MilitaryAirport

__all__ = [
    "Base",
    "Flight",
    "Location",
    "LocationType",
    "MilitaryAirport",
    "SeatStatus",
]
