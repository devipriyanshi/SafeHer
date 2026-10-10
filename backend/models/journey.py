import enum
from sqlalchemy import ForeignKey, String, Float, DateTime, Enum, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from backend.database import Base


class JourneyStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"       # arrival time passed, user not yet confirmed


class SafetyJourney(Base):
    """
    A live journey instance started from a SafetyPlan or ad-hoc.
    Tracks lifecycle: active → completed/cancelled/expired.
    """
    __tablename__ = "safety_journeys"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    safety_plan_id: Mapped[int | None] = mapped_column(ForeignKey("safety_plans.id"), nullable=True)

    origin: Mapped[str] = mapped_column(String(200))
    destination: Mapped[str] = mapped_column(String(200))
    expected_duration_minutes: Mapped[int] = mapped_column(Integer)

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expected_arrival_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Last known location — only stored if user has enabled store_journey_location
    last_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_location_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[JourneyStatus] = mapped_column(Enum(JourneyStatus), default=JourneyStatus.ACTIVE)
    extension_count: Mapped[int] = mapped_column(Integer, default=0)

    user: Mapped["User"] = relationship(back_populates="journeys")
    safety_plan: Mapped["SafetyPlan"] = relationship(back_populates="journeys")
    signals: Mapped[list["SafetySignal"]] = relationship(back_populates="journey", cascade="all, delete-orphan")
    assessments: Mapped[list["SafetyAssessment"]] = relationship(back_populates="journey", cascade="all, delete-orphan")
