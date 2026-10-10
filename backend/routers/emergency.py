from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.auth.dependencies import get_current_user
from backend.models.user import User
from backend.schemas.emergency import SOSRequest, EmergencyEventResponse, EmergencyDetailResponse
from backend.services import emergency_service as svc

router = APIRouter(prefix="/api/emergency", tags=["Emergency"])


@router.post("/sos", response_model=EmergencyEventResponse, status_code=status.HTTP_201_CREATED)
async def trigger_sos(
    payload: SOSRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await svc.trigger_sos(current_user.id, current_user.full_name, payload, db)


@router.post("/{event_id}/cancel", response_model=EmergencyEventResponse)
async def cancel_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await svc.cancel_event(event_id, current_user.id, db)


@router.get("/history", response_model=list[EmergencyEventResponse])
async def get_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_history(current_user.id, db)


@router.get("/{event_id}", response_model=EmergencyDetailResponse)
async def get_event(
    event_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_event_detail(event_id, current_user.id, db)
