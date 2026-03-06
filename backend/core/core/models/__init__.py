from core.enums.document import DocumentType
from core.enums.location import LocationType

from .base import Base
from .flight import Flight, SeatStatus
from .location import Location, MilitaryAirport
from .terminal_document import TerminalDocument

__all__ = [
    "Base",
    "DocumentType",
    "Flight",
    "Location",
    "LocationType",
    "MilitaryAirport",
    "SeatStatus",
    "TerminalDocument",
]
