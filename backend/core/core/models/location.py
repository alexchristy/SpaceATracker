from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import mapped_column

from core.enums.location import LocationType

from .base import Base

if TYPE_CHECKING:
    from sqlalchemy.orm import Mapped


class Location(Base):
    """Standardized location."""

    __tablename__ = "locations"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    location_type: Mapped[LocationType] = mapped_column(String(50), nullable=False)

    latitude: Mapped[float]
    longitude: Mapped[float]

    timezone: Mapped[str] = mapped_column(String(50))

    country: Mapped[str] = mapped_column(String(100))
    state_or_province: Mapped[str | None] = mapped_column(String(100))

    __mapper_args__ = {  # noqa: RUF012
        "polymorphic_identity": "location",
        "polymorphic_on": "location_type",
    }


class CivilianAirport(Location):
    """Civilian airport location."""

    iata_code: Mapped[str | None] = mapped_column(String(3))
    icao_code: Mapped[str | None] = mapped_column(String(4))

    __mapper_args__ = {  # noqa: RUF012
        "polymorphic_identity": LocationType.CIVILIAN_AIRPORT,
    }


class MilitaryAirport(Location):
    """Military airport location."""

    icao_code: Mapped[str | None] = mapped_column(String(4))
    website_url: Mapped[str | None] = mapped_column(String(2048))

    __mapper_args__ = {  # noqa: RUF012
        "polymorphic_identity": LocationType.MILITARY_AIRPORT,
    }


class City(Location):
    """City location."""

    __mapper_args__ = {  # noqa: RUF012
        "polymorphic_identity": LocationType.CITY,
    }
