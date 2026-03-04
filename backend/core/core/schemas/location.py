import zoneinfo
from typing import Annotated

from pydantic import AfterValidator, AnyHttpUrl, BaseModel, ConfigDict, Field

from core.enums.location import LocationType


def generate_location_id(location_name: str) -> str:
    """Derives a deterministic, URL-safe ID from a location name."""
    return location_name.lower().replace(" ", "-").replace(",", "")


class LocationBase(BaseModel):
    name: Annotated[str, AfterValidator(lambda s: s.strip())] | None = None
    raw_location: Annotated[str, AfterValidator(lambda s: s.strip())] | None = None
    location_type: LocationType
    latitude: Annotated[float, Field(ge=-90.0, le=90.0)] | None = None
    longitude: Annotated[float, Field(ge=-180.0, le=180.0)] | None = None
    timezone: zoneinfo.ZoneInfo | None = None
    country: str | None = None
    state_or_province: str | None = None


class LocationCreate(LocationBase):
    id: str


class LocationUpdate(BaseModel):
    name: Annotated[str, AfterValidator(lambda s: s.strip())] | None = None
    latitude: Annotated[float, Field(ge=-90.0, le=90.0)] | None = None
    longitude: Annotated[float, Field(ge=-180.0, le=180.0)] | None = None
    timezone: zoneinfo.ZoneInfo | None = None
    country: str | None = None
    state_or_province: str | None = None


class LocationRead(LocationBase):
    id: str
    model_config = ConfigDict(from_attributes=True)


class CivilianAirportBase(LocationBase):
    location_type: LocationType = LocationType.CIVILIAN_AIRPORT
    iata_code: Annotated[str, Field(pattern=r"^[A-Z]{3}$")] | None = None
    icao_code: Annotated[str, Field(pattern=r"^[A-Z]{4}$")] | None = None


class CivilianAirportCreate(CivilianAirportBase, LocationCreate):
    pass


class CivilianAirportUpdate(LocationUpdate):
    iata_code: Annotated[str, Field(pattern=r"^[A-Z]{3}$")] | None = None
    icao_code: Annotated[str, Field(pattern=r"^[A-Z]{4}$")] | None = None


class CivilianAirportRead(CivilianAirportBase, LocationRead):
    pass


class MilitaryAirportBase(LocationBase):
    location_type: LocationType = LocationType.MILITARY_AIRPORT
    icao_code: Annotated[str, Field(pattern=r"^[A-Z]{4}$")] | None = None
    website_url: AnyHttpUrl | None = None
    terminal_group: str | None = None


class MilitaryAirportCreate(MilitaryAirportBase, LocationCreate):
    pass


class MilitaryAirportUpdate(LocationUpdate):
    icao_code: Annotated[str, Field(pattern=r"^[A-Z]{4}$")] | None = None
    website_url: AnyHttpUrl | None = None


class MilitaryAirportRead(MilitaryAirportBase, LocationRead):
    pass
