from enum import StrEnum


class LocationType(StrEnum):
    """Type of location."""

    CIVILIAN_AIRPORT = "civilian_airport"
    MILITARY_AIRPORT = "military_airport"
    CITY = "city"
