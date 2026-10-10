import enum
from sqlalchemy import ForeignKey, String, Enum, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from backend.database import Base


class SignalType(str, enum.Enum):
    JOURNEY_DELAY = "journey_delay"
    ROUTE_DEVIATION = "route_deviation"
    MANUAL_CHECK = "manual_check"
    REPEATED_WARNING = "repeated_warning"
    JOURNEY_EXPIRED = "journey_expired"
    USER_TRIGGERED = "user_triggered"


class SignalSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class SafetySignal(Base):
    """
    A structured safety event observed during a journey.
    Signals feed into the AI assessment — they do NOT trigger alerts directly.
    """
    __tablename__ = "safety_signals"

    id: Mapped[int] = mapped_column(primary_key=True)
    journey_id: Mapped[int] = mapped_column(ForeignKey("safety_journeys.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    signal_type: Mapped[SignalType] = mapped_column(Enum(SignalType))
    severity: Mapped[SignalSeverity] = mapped_column(Enum(SignalSeverity), default=SignalSeverity.LOW)
    description: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(100))   # e.g. "journey_engine", "user"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    journey: Mapped["SafetyJourney"] = relationship(back_populates="signals")
