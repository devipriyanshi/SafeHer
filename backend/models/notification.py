import enum
from sqlalchemy import ForeignKey, String, Boolean, Enum, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from backend.database import Base


class NotificationChannel(str, enum.Enum):
    EMAIL = "email"
    SMS = "sms"
    MOCK = "mock"


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    emergency_event_id: Mapped[int] = mapped_column(ForeignKey("emergency_events.id"))
    contact_id: Mapped[int | None] = mapped_column(ForeignKey("emergency_contacts.id"), nullable=True)

    channel: Mapped[NotificationChannel] = mapped_column(Enum(NotificationChannel))
    recipient: Mapped[str] = mapped_column(String(150))   # email or phone
    success: Mapped[bool] = mapped_column(Boolean, default=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    emergency_event: Mapped["EmergencyEvent"] = relationship(back_populates="notification_logs")
