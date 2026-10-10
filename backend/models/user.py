from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime, timezone
from backend.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    privacy_setting: Mapped["PrivacySetting"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    safety_plans: Mapped[list["SafetyPlan"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    journeys: Mapped[list["SafetyJourney"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    contacts: Mapped[list["EmergencyContact"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    emergency_events: Mapped[list["EmergencyEvent"]] = relationship(back_populates="user", cascade="all, delete-orphan")
