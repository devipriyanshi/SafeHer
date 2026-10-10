import enum
from sqlalchemy import ForeignKey, String, Float, Enum, DateTime, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from backend.database import Base


class EmergencyEventType(str, enum.Enum):
    MANUAL_SOS = "manual_sos"
    VOICE_SOS = "voice_sos"
    JOURNEY_ESCALATION = "journey_escalation"
    USER_ALERT = "user_alert"


class EmergencyEventStatus(str, enum.Enum):
    ACTIVE = "active"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"


class EmergencyEvent(Base):
    __tablename__ = "emergency_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    journey_id: Mapped[int | None] = mapped_column(ForeignKey("safety_journeys.id"), nullable=True)

    event_type: Mapped[EmergencyEventType] = mapped_column(Enum(EmergencyEventType))
    status: Mapped[EmergencyEventStatus] = mapped_column(Enum(EmergencyEventStatus), default=EmergencyEventStatus.ACTIVE)

    # Location at time of SOS — only if user has location permission enabled
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_link: Mapped[str | None] = mapped_column(String(300), nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    notifications_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="emergency_events")
    notification_logs: Mapped[list["NotificationLog"]] = relationship(back_populates="emergency_event", cascade="all, delete-orphan")
