from sqlalchemy import ForeignKey, String, Integer, Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from backend.database import Base


class SafetyPlan(Base):
    """
    A reusable safety profile for a recurring journey.
    e.g. 'College → Home' with expected duration and trusted contact.
    """
    __tablename__ = "safety_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(150))          # e.g. "College to Home"
    origin: Mapped[str] = mapped_column(String(200))
    destination: Mapped[str] = mapped_column(String(200))
    expected_duration_minutes: Mapped[int] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["User"] = relationship(back_populates="safety_plans")
    journeys: Mapped[list["SafetyJourney"]] = relationship(back_populates="safety_plan")
