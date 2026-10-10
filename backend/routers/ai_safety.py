from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.auth.dependencies import get_current_user
from backend.models.user import User
from backend.schemas.assessment import AnalyzeRequest, AssessmentResponse
from backend.services import ai_service as svc

router = APIRouter(prefix="/api/ai", tags=["AI Safety Assistance"])


@router.post("/analyze", response_model=AssessmentResponse, status_code=status.HTTP_201_CREATED)
async def analyze(
    payload: AnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await svc.analyze_journey(payload.journey_id, current_user.id, db)


@router.get("/assessment/{journey_id}", response_model=AssessmentResponse | None)
async def get_assessment(
    journey_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_latest_assessment(journey_id, current_user.id, db)
