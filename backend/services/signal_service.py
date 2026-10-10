from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from backend.models.signal import SafetySignal
from backend.models.journey import SafetyJourney, JourneyStatus
from backend.schemas.signal import SignalCreateRequest


async def create_signal(user_id: int, payload: SignalCreateRequest, db: AsyncSession) -> SafetySignal:
    # Verify journey belongs to user and is active/expired
    result = await db.execute(
        select(SafetyJourney).where(SafetyJourney.id == payload.journey_id)
    )
    journey = result.scalar_one_or_none()

    if not journey:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journey not found")
    if journey.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    if journey.status not in (JourneyStatus.ACTIVE, JourneyStatus.EXPIRED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Signals can only be added to active or expired journeys",
        )

    signal = SafetySignal(
        journey_id=payload.journey_id,
        user_id=user_id,
        signal_type=payload.signal_type,
        severity=payload.severity,
        description=payload.description,
        source="user",
    )
    db.add(signal)
    await db.commit()
    await db.refresh(signal)
    return signal


async def get_journey_signals(journey_id: int, user_id: int, db: AsyncSession) -> list[SafetySignal]:
    # Verify journey ownership
    result = await db.execute(select(SafetyJourney).where(SafetyJourney.id == journey_id))
    journey = result.scalar_one_or_none()

    if not journey:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journey not found")
    if journey.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    signals = await db.execute(
        select(SafetySignal)
        .where(SafetySignal.journey_id == journey_id)
        .order_by(SafetySignal.created_at)
    )
    return list(signals.scalars().all())
