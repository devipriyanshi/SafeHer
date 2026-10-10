from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from backend.models.journey import SafetyJourney
from backend.models.signal import SafetySignal
from backend.models.assessment import SafetyAssessment, SafetyIndication
from backend.ai_safety.predictor import predictor


async def analyze_journey(journey_id: int, user_id: int, db: AsyncSession) -> SafetyAssessment:
    # Verify journey ownership
    result = await db.execute(select(SafetyJourney).where(SafetyJourney.id == journey_id))
    journey = result.scalar_one_or_none()

    if not journey:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journey not found")
    if journey.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    # Fetch all signals for this journey
    sig_result = await db.execute(
        select(SafetySignal).where(SafetySignal.journey_id == journey_id)
    )
    signals = list(sig_result.scalars().all())

    # Run prediction
    result_dict = predictor.predict(signals, journey.extension_count)

    assessment = SafetyAssessment(
        journey_id=journey_id,
        user_id=user_id,
        indication=SafetyIndication(result_dict["indication"]),
        assistance_score=result_dict["assistance_score"],
        explanation=result_dict["explanation"],
        suggested_action=result_dict["suggested_action"],
        contributing_signal_ids=[s.id for s in signals],
        ai_available=result_dict["ai_available"],
    )
    db.add(assessment)
    await db.commit()
    await db.refresh(assessment)
    return assessment


async def get_latest_assessment(journey_id: int, user_id: int, db: AsyncSession) -> SafetyAssessment | None:
    result = await db.execute(select(SafetyJourney).where(SafetyJourney.id == journey_id))
    journey = result.scalar_one_or_none()

    if not journey:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journey not found")
    if journey.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    assessment_result = await db.execute(
        select(SafetyAssessment)
        .where(SafetyAssessment.journey_id == journey_id)
        .order_by(SafetyAssessment.created_at.desc())
    )
    return assessment_result.scalars().first()
