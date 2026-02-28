from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import mapped_column, relationship

from .base import Base

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.orm import Mapped

    from core.enums.seats import SeatStatus

    from .location import Location


class Flight(Base):
    """Flight database table."""

    __tablename__ = "flights"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)

    origin_id: Mapped[str] = mapped_column(String(50), ForeignKey("location.id"))
    destination_id: Mapped[str] = mapped_column(String(50), ForeignKey("location.id"))

    origin: Mapped[Location] = relationship(foreign_keys=[origin_id])
    destination: Mapped[Location] = relationship(foreign_keys=[destination_id])

    roll_call_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    seats_available: Mapped[int] = mapped_column(Integer)
    seat_status: Mapped[SeatStatus] = mapped_column(String(1))

    source_url: Mapped[str] = mapped_column(String(2048))
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    raw_seats: Mapped[str] = mapped_column(String(255))
    raw_origin: Mapped[str] = mapped_column(String(255))
    raw_destination: Mapped[str] = mapped_column(String(255))
