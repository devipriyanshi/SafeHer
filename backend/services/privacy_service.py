from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from backend.models.privacy import PrivacySetting
from backend.schemas.privacy import PrivacySettingUpdate, PrivacySummaryResponse, PrivacySummaryItem


async def get_privacy(user_id: int, db: AsyncSession) -> PrivacySetting:
    result = await db.execute(
        select(PrivacySetting).where(PrivacySetting.user_id == user_id)
    )
    setting = result.scalar_one_or_none()
    if not setting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Privacy settings not found")
    return setting


async def update_privacy(user_id: int, payload: PrivacySettingUpdate, db: AsyncSession) -> PrivacySetting:
    setting = await get_privacy(user_id, db)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(setting, field, value)
    await db.commit()
    await db.refresh(setting)
    return setting


async def get_privacy_summary(user_id: int, db: AsyncSession) -> PrivacySummaryResponse:
    s = await get_privacy(user_id, db)

    items = [
        PrivacySummaryItem(
            setting="Location Access",
            status="Enabled" if s.location_access_enabled else "Disabled",
            description="SafeHer can read your device location during a journey.",
        ),
        PrivacySummaryItem(
            setting="Location Sharing",
            status="Enabled" if s.location_sharing_enabled else "Disabled",
            description="Your location is shared with trusted contacts during emergencies.",
        ),
        PrivacySummaryItem(
            setting="Store Journey Location",
            status="Enabled" if s.store_journey_location else "Disabled",
            description="Location checkpoints are saved to your journey history.",
        ),
        PrivacySummaryItem(
            setting="Voice Assistance",
            status="Enabled" if s.voice_assistance_enabled else "Disabled",
            description="Microphone is used to detect your configured voice trigger phrase.",
        ),
        PrivacySummaryItem(
            setting="Location in Alerts",
            status="Included" if s.include_location_in_alert else "Excluded",
            description="Your location link is included in emergency alert messages.",
        ),
        PrivacySummaryItem(
            setting="Journey Details in Alerts",
            status="Included" if s.include_journey_details_in_alert else "Excluded",
            description="Origin, destination and journey name are included in alerts.",
        ),
        PrivacySummaryItem(
            setting="Auto-Escalate on Expiry",
            status="Enabled" if s.auto_escalate_on_journey_expiry else "Disabled",
            description="Automatically notifies contacts if journey expires without response.",
        ),
        PrivacySummaryItem(
            setting="Data Retention",
            status=f"{s.safety_event_retention_days} days" if s.safety_event_retention_days > 0 else "Not retained",
            description="How long safety events are kept in your history.",
        ),
    ]

    collected = []
    not_collected = []

    if s.location_access_enabled:
        collected.append("Device location (during active journey only)")
    else:
        not_collected.append("Device location")

    if s.store_journey_location:
        collected.append("Journey location checkpoints")
    else:
        not_collected.append("Journey location history")

    if s.voice_assistance_enabled:
        collected.append("Microphone audio (processed locally for trigger phrase)")
    else:
        not_collected.append("Microphone / audio data")

    collected.append("Journey metadata (origin, destination, duration)")
    collected.append("Safety signals (journey events)")

    if s.safety_event_retention_days == 0:
        not_collected.append("Long-term safety event history")

    return PrivacySummaryResponse(
        items=items,
        data_collected=collected,
        data_not_collected=not_collected,
    )
