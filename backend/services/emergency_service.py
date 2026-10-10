from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from backend.models.emergency import EmergencyEvent, EmergencyEventStatus
from backend.models.notification import NotificationLog
from backend.models.privacy import PrivacySetting
from backend.schemas.emergency import SOSRequest
from backend.services.contact_service import get_active_contacts
from backend.services.notification_service import dispatch_alert


def _make_location_link(lat: float, lon: float) -> str:
    return f"https://maps.google.com/?q={lat},{lon}"


async def trigger_sos(user_id: int, user_name: str, payload: SOSRequest, db: AsyncSession) -> EmergencyEvent:
    priv_result = await db.execute(
        select(PrivacySetting).where(PrivacySetting.user_id == user_id)
    )
    privacy = priv_result.scalar_one_or_none()

    include_location = bool(privacy and privacy.include_location_in_alert)
    include_journey = bool(privacy and privacy.include_journey_details_in_alert)

    lat = payload.latitude if include_location else None
    lon = payload.longitude if include_location else None
    location_link = _make_location_link(lat, lon) if (lat and lon) else None

    event = EmergencyEvent(
        user_id=user_id,
        journey_id=payload.journey_id if include_journey else None,
        event_type=payload.event_type,
        status=EmergencyEventStatus.ACTIVE,
        latitude=lat,
        longitude=lon,
        location_link=location_link,
        notes=payload.notes,
    )
    db.add(event)
    await db.flush()

    contacts = await get_active_contacts(user_id, db)
    notification_results = []

    if contacts:
        notification_results = dispatch_alert(event, contacts, user_name, include_location)
        event.notifications_sent = True

    for nr in notification_results:
        db.add(NotificationLog(
            emergency_event_id=event.id,
            contact_id=nr["contact_id"],
            channel=nr["channel"],
            recipient=nr["recipient"],
            success=nr["success"],
            error_message=nr["error_message"],
        ))

    await db.commit()
    await db.refresh(event)
    return event


async def cancel_event(event_id: int, user_id: int, db: AsyncSession) -> EmergencyEvent:
    result = await db.execute(select(EmergencyEvent).where(EmergencyEvent.id == event_id))
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emergency event not found")
    if event.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if event.status != EmergencyEventStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Event is already {event.status.value}",
        )

    event.status = EmergencyEventStatus.CANCELLED
    event.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(event)
    return event


async def get_history(user_id: int, db: AsyncSession) -> list[EmergencyEvent]:
    result = await db.execute(
        select(EmergencyEvent)
        .where(EmergencyEvent.user_id == user_id)
        .order_by(EmergencyEvent.created_at.desc())
    )
    return list(result.scalars().all())


async def get_event_detail(event_id: int, user_id: int, db: AsyncSession) -> EmergencyEvent:
    result = await db.execute(select(EmergencyEvent).where(EmergencyEvent.id == event_id))
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Emergency event not found")
    if event.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return event
