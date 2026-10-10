from sqlalchemy import ForeignKey, Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


class PrivacySetting(Base):
    """
    Controls what data SafeHer collects and shares.
    Privacy is a core feature — not an afterthought.
    """
    __tablename__ = "privacy_settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True)

    # Location permissions
    location_access_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    location_sharing_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    store_journey_location: Mapped[bool] = mapped_column(Boolean, default=False)

    # Microphone
    voice_assistance_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    # Alert content control
    include_location_in_alert: Mapped[bool] = mapped_column(Boolean, default=True)
    include_journey_details_in_alert: Mapped[bool] = mapped_column(Boolean, default=True)

    # Data retention (days); 0 = do not retain
    safety_event_retention_days: Mapped[int] = mapped_column(Integer, default=30)

    # Auto-escalation: user must explicitly opt in
    auto_escalate_on_journey_expiry: Mapped[bool] = mapped_column(Boolean, default=False)

    # Custom voice phrase for voice SOS
    voice_trigger_phrase: Mapped[str] = mapped_column(String(100), default="help me")

    user: Mapped["User"] = relationship(back_populates="privacy_setting")
