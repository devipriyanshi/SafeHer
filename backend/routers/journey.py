from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.auth.dependencies import get_current_user
from backend.models.user import User
from backend.schemas.journey import (
    JourneyStartRequest, JourneyExtendRequest,
    JourneyResponse, JourneyTimelineResponse,
)
from backend.services import journey_service as svc

router = APIRouter(prefix="/api/journeys", tags=["Safety Journey"])


@router.post("/start", response_model=JourneyResponse, status_code=status.HTTP_201_CREATED)
async def start_journey(
    payload: JourneyStartRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await svc.start_journey(current_user.id, payload, db)


@router.get("/active", response_model=JourneyResponse | None)
async def active_journey(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_active_journey(current_user.id, db)


@router.get("/{journey_id}", response_model=JourneyResponse)
async def get_journey(
    journey_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_journey(journey_id, current_user.id, db)


@router.post("/{journey_id}/safe", response_model=JourneyResponse)
async def mark_safe(
    journey_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await svc.mark_safe(journey_id, current_user.id, db)


@router.post("/{journey_id}/extend", response_model=JourneyResponse)
async def extend_journey(
    journey_id: int,
    payload: JourneyExtendRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await svc.extend_journey(journey_id, current_user.id, payload, db)


@router.post("/{journey_id}/cancel", response_model=JourneyResponse)
async def cancel_journey(
    journey_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await svc.cancel_journey(journey_id, current_user.id, db)


@router.post("/{journey_id}/complete", response_model=JourneyResponse)
async def complete_journey(
    journey_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await svc.complete_journey(journey_id, current_user.id, db)


@router.get("/{journey_id}/timeline", response_model=JourneyTimelineResponse)
async def journey_timeline(
    journey_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await svc.build_timeline(journey_id, current_user.id, db)
