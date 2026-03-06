from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.enums.seats import SeatStatus

from .base import Base

if TYPE_CHECKING:
    from .location import Location
    from .terminal_document import TerminalDocument


class Flight(Base):
    """Flight database table."""

    __tablename__ = "flights"

    id: Mapped[str] = mapped_column(String(50), primary_key=True)

    terminal_doc_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("terminal_documents.id")
    )
    origin_id: Mapped[str] = mapped_column(String(50), ForeignKey("locations.id"))
    destination_id: Mapped[str] = mapped_column(String(50), ForeignKey("locations.id"))

    terminal_document: Mapped[TerminalDocument] = relationship()
    origin: Mapped[Location] = relationship(foreign_keys=[origin_id])
    destination: Mapped[Location] = relationship(foreign_keys=[destination_id])

    roll_call_time: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    seats_available: Mapped[int] = mapped_column(Integer)
    seat_status: Mapped[SeatStatus] = mapped_column(String(1))

    raw_seats: Mapped[str] = mapped_column(String(255))
    raw_origin: Mapped[str] = mapped_column(String(255))
    raw_destination: Mapped[str] = mapped_column(String(255))
