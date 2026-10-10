from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.auth.dependencies import get_current_user
from backend.models.user import User
from backend.schemas.privacy import PrivacySettingUpdate, PrivacySettingResponse, PrivacySummaryResponse
from backend.services import privacy_service as svc

router = APIRouter(prefix="/api/privacy", tags=["Privacy"])


@router.get("", response_model=PrivacySettingResponse)
async def get_privacy(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_privacy(current_user.id, db)


@router.put("", response_model=PrivacySettingResponse)
async def update_privacy(
    payload: PrivacySettingUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await svc.update_privacy(current_user.id, payload, db)


@router.get("/summary", response_model=PrivacySummaryResponse)
async def privacy_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_privacy_summary(current_user.id, db)
