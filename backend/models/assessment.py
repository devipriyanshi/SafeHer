import enum
from sqlalchemy import ForeignKey, String, Integer, Float, Enum, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from backend.database import Base


class SafetyIndication(str, enum.Enum):
    NORMAL = "normal"
    ATTENTION_RECOMMENDED = "attention_recommended"
    POTENTIALLY_UNUSUAL = "potentially_unusual"


class SafetyAssessment(Base):
    """
    AI-generated assistive safety indication for a journey.
    This is an ASSISTIVE signal — not a danger verdict.
    The user decides what action to take.
    """
    __tablename__ = "safety_assessments"

    id: Mapped[int] = mapped_column(primary_key=True)
    journey_id: Mapped[int] = mapped_column(ForeignKey("safety_journeys.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    indication: Mapped[SafetyIndication] = mapped_column(Enum(SafetyIndication))

    # 0–100 assistive score (NOT a danger measurement)
    assistance_score: Mapped[float] = mapped_column(Float, default=0.0)

    # Human-readable explanation of why this indication was produced
    explanation: Mapped[str] = mapped_column(Text)

    # Which signals contributed (stored as JSON list of signal IDs)
    contributing_signal_ids: Mapped[list] = mapped_column(JSON, default=list)

    # Suggested action shown to user
    suggested_action: Mapped[str] = mapped_column(String(300))

    ai_available: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    journey: Mapped["SafetyJourney"] = relationship(back_populates="assessments")
