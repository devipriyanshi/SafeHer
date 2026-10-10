from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from backend.models.journey import SafetyJourney, JourneyStatus
from backend.models.signal import SafetySignal, SignalType, SignalSeverity
from backend.models.safety_plan import SafetyPlan
from backend.schemas.journey import JourneyStartRequest, JourneyExtendRequest, TimelineEvent


# ── helpers ──────────────────────────────────────────────────────────────────

async def _get_journey_or_403(journey_id: int, user_id: int, db: AsyncSession) -> SafetyJourney:
    result = await db.execute(select(SafetyJourney).where(SafetyJourney.id == journey_id))
    journey = result.scalar_one_or_none()
    if not journey:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journey not found")
    if journey.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return journey


def _require_active(journey: SafetyJourney) -> None:
    if journey.status not in (JourneyStatus.ACTIVE, JourneyStatus.EXPIRED):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Journey is already {journey.status.value}",
        )


async def _emit_signal(
    journey: SafetyJourney,
    signal_type: SignalType,
    severity: SignalSeverity,
    description: str,
    db: AsyncSession,
) -> None:
    db.add(SafetySignal(
        journey_id=journey.id,
        user_id=journey.user_id,
        signal_type=signal_type,
        severity=severity,
        description=description,
        source="journey_engine",
    ))


# ── core operations ───────────────────────────────────────────────────────────

async def start_journey(user_id: int, payload: JourneyStartRequest, db: AsyncSession) -> SafetyJourney:
    # Only one active journey at a time
    existing = await db.execute(
        select(SafetyJourney).where(
            SafetyJourney.user_id == user_id,
            SafetyJourney.status.in_([JourneyStatus.ACTIVE, JourneyStatus.EXPIRED]),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have an active journey. Complete or cancel it first.",
        )

    # Validate safety_plan_id belongs to user
    if payload.safety_plan_id:
        plan = await db.execute(
            select(SafetyPlan).where(SafetyPlan.id == payload.safety_plan_id, SafetyPlan.user_id == user_id)
        )
        if not plan.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Safety plan not found")

    now = datetime.now(timezone.utc)
    journey = SafetyJourney(
        user_id=user_id,
        safety_plan_id=payload.safety_plan_id,
        origin=payload.origin,
        destination=payload.destination,
        expected_duration_minutes=payload.expected_duration_minutes,
        started_at=now,
        expected_arrival_at=now + timedelta(minutes=payload.expected_duration_minutes),
        status=JourneyStatus.ACTIVE,
    )
    db.add(journey)
    await db.commit()
    await db.refresh(journey)
    return journey


async def get_active_journey(user_id: int, db: AsyncSession) -> SafetyJourney | None:
    result = await db.execute(
        select(SafetyJourney).where(
            SafetyJourney.user_id == user_id,
            SafetyJourney.status.in_([JourneyStatus.ACTIVE, JourneyStatus.EXPIRED]),
        )
    )
    return result.scalar_one_or_none()


async def get_journey(journey_id: int, user_id: int, db: AsyncSession) -> SafetyJourney:
    return await _get_journey_or_403(journey_id, user_id, db)


async def mark_safe(journey_id: int, user_id: int, db: AsyncSession) -> SafetyJourney:
    journey = await _get_journey_or_403(journey_id, user_id, db)
    _require_active(journey)
    # Emit a user-triggered safe signal
    await _emit_signal(
        journey, SignalType.USER_TRIGGERED, SignalSeverity.LOW,
        "User confirmed they are safe during journey.", db,
    )
    await db.commit()
    await db.refresh(journey)
    return journey


async def extend_journey(journey_id: int, user_id: int, payload: JourneyExtendRequest, db: AsyncSession) -> SafetyJourney:
    journey = await _get_journey_or_403(journey_id, user_id, db)
    _require_active(journey)

    journey.expected_arrival_at += timedelta(minutes=payload.extend_by_minutes)
    journey.expected_duration_minutes += payload.extend_by_minutes
    journey.extension_count += 1

    # Multiple extensions are a mild signal
    severity = SignalSeverity.MEDIUM if journey.extension_count >= 2 else SignalSeverity.LOW
    await _emit_signal(
        journey, SignalType.JOURNEY_DELAY, severity,
        f"Journey extended by {payload.extend_by_minutes} minutes (extension #{journey.extension_count}).", db,
    )

    if journey.status == JourneyStatus.EXPIRED:
        journey.status = JourneyStatus.ACTIVE

    await db.commit()
    await db.refresh(journey)
    return journey


async def cancel_journey(journey_id: int, user_id: int, db: AsyncSession) -> SafetyJourney:
    journey = await _get_journey_or_403(journey_id, user_id, db)
    _require_active(journey)
    journey.status = JourneyStatus.CANCELLED
    journey.completed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(journey)
    return journey


async def complete_journey(journey_id: int, user_id: int, db: AsyncSession) -> SafetyJourney:
    journey = await _get_journey_or_403(journey_id, user_id, db)
    _require_active(journey)
    journey.status = JourneyStatus.COMPLETED
    journey.completed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(journey)
    return journey


async def check_and_expire_journeys(db: AsyncSession) -> list[int]:
    """
    Called periodically (or on-demand) to mark overdue journeys as EXPIRED.
    Returns list of expired journey IDs so the caller can notify users.
    IMPORTANT: EXPIRED ≠ danger. It only means arrival time has passed.
    """
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(SafetyJourney).where(
            SafetyJourney.status == JourneyStatus.ACTIVE,
            SafetyJourney.expected_arrival_at < now,
        )
    )
    expired_ids = []
    for journey in result.scalars().all():
        journey.status = JourneyStatus.EXPIRED
        await _emit_signal(
            journey, SignalType.JOURNEY_EXPIRED, SignalSeverity.MEDIUM,
            "Journey arrival time has passed without user confirmation.", db,
        )
        expired_ids.append(journey.id)

    if expired_ids:
        await db.commit()
    return expired_ids


# ── timeline builder ──────────────────────────────────────────────────────────

async def build_timeline(journey_id: int, user_id: int, db: AsyncSession) -> dict:
    journey = await _get_journey_or_403(journey_id, user_id, db)

    events: list[TimelineEvent] = [
        TimelineEvent(timestamp=journey.started_at, event="Journey Started",
                      detail=f"{journey.origin} → {journey.destination}")
    ]

    # Pull signals for this journey ordered by time
    sig_result = await db.execute(
        select(SafetySignal)
        .where(SafetySignal.journey_id == journey_id)
        .order_by(SafetySignal.created_at)
    )
    for sig in sig_result.scalars().all():
        events.append(TimelineEvent(
            timestamp=sig.created_at,
            event=sig.signal_type.value.replace("_", " ").title(),
            detail=sig.description,
        ))

    if journey.completed_at:
        label = {
            JourneyStatus.COMPLETED: "Journey Completed",
            JourneyStatus.CANCELLED: "Journey Cancelled",
        }.get(journey.status, "Journey Ended")
        events.append(TimelineEvent(timestamp=journey.completed_at, event=label))

    return {"journey_id": journey_id, "status": journey.status, "timeline": events}
