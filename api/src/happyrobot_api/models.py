from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from happyrobot_api.db import Base


class Load(Base):
    __tablename__ = "loads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    reference_number: Mapped[str] = mapped_column(String(64), unique=True, index=True)

    # Bridge-spec fields
    type: Mapped[str] = mapped_column(String(16), default="owned")
    status: Mapped[str] = mapped_column(String(24), default="available", index=True)
    equipment_type: Mapped[str] = mapped_column(String(32), index=True)
    commodity_type: Mapped[str] = mapped_column(String(64))
    is_partial: Mapped[bool] = mapped_column(Boolean, default=False)
    is_hazmat: Mapped[bool] = mapped_column(Boolean, default=False)

    posted_carrier_rate: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    max_buy: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    weight: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    number_of_pieces: Mapped[int | None] = mapped_column(Integer, nullable=True)
    miles: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dimensions: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sale_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Origin stop
    origin_city: Mapped[str] = mapped_column(String(64), index=True)
    origin_state: Mapped[str] = mapped_column(String(16), index=True)
    origin_zip: Mapped[str] = mapped_column(String(16))
    origin_country: Mapped[str] = mapped_column(String(8), default="US")
    origin_open: Mapped[datetime] = mapped_column(DateTime)
    origin_close: Mapped[datetime] = mapped_column(DateTime)

    # Destination stop
    destination_city: Mapped[str] = mapped_column(String(64), index=True)
    destination_state: Mapped[str] = mapped_column(String(16), index=True)
    destination_zip: Mapped[str] = mapped_column(String(16))
    destination_country: Mapped[str] = mapped_column(String(8), default="US")
    destination_open: Mapped[datetime] = mapped_column(DateTime)
    destination_close: Mapped[datetime] = mapped_column(DateTime)

    # Optional contact on the load (broker-side)
    contact: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Carrier(Base):
    """Cache of FMCSA lookups keyed by MC number."""

    __tablename__ = "carriers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mc_number: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    dot_number: Mapped[str | None] = mapped_column(String(16), index=True, nullable=True)
    carrier_name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(16))  # active | fail | inactive | in_review
    allowed_to_operate: Mapped[bool] = mapped_column(Boolean, default=False)
    fmcsa_raw: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    cached_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Call(Base):
    """One row per completed call, populated by HappyRobot webhook."""

    __tablename__ = "calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    external_call_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    mc_number: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    carrier_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    load_reference_number: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    outcome: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    sentiment: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)

    final_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    loadboard_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    rounds_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    agreement_reached: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_fields: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    offers: Mapped[list["Offer"]] = relationship(
        back_populates="call", cascade="all, delete-orphan"
    )


class Offer(Base):
    """One row per negotiation round, logged by the agent during the call."""

    __tablename__ = "offers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    call_id: Mapped[int | None] = mapped_column(
        ForeignKey("calls.id", ondelete="CASCADE"), nullable=True, index=True
    )
    mc_number: Mapped[str] = mapped_column(String(16), index=True)
    load_reference_number: Mapped[str] = mapped_column(String(64), index=True)
    round_number: Mapped[int] = mapped_column(Integer)
    carrier_offer: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    agent_counter: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    decision: Mapped[str] = mapped_column(String(16))  # accept | counter | decline
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    call: Mapped["Call | None"] = relationship(back_populates="offers")
