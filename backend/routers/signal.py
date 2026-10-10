from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.auth.dependencies import get_current_user
from backend.models.user import User
from backend.schemas.signal import SignalCreateRequest, SignalResponse
from backend.services import signal_service as svc

router = APIRouter(prefix="/api/signals", tags=["Safety Signals"])


@router.post("", response_model=SignalResponse, status_code=status.HTTP_201_CREATED)
async def create_signal(
    payload: SignalCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await svc.create_signal(current_user.id, payload, db)


@router.get("/{journey_id}", response_model=list[SignalResponse])
async def get_signals(
    journey_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_journey_signals(journey_id, current_user.id, db)
