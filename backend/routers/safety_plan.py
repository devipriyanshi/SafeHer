from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.auth.dependencies import get_current_user
from backend.models.user import User
from backend.schemas.safety_plan import SafetyPlanCreate, SafetyPlanUpdate, SafetyPlanResponse
from backend.services import safety_plan_service as svc

router = APIRouter(prefix="/api/safety-plans", tags=["Safety Plans"])


@router.get("", response_model=list[SafetyPlanResponse])
async def list_plans(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_user_plans(current_user.id, db)


@router.get("/{plan_id}", response_model=SafetyPlanResponse)
async def get_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await svc.get_plan_or_403(plan_id, current_user.id, db)


@router.post("", response_model=SafetyPlanResponse, status_code=status.HTTP_201_CREATED)
async def create_plan(
    payload: SafetyPlanCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await svc.create_plan(current_user.id, payload, db)


@router.put("/{plan_id}", response_model=SafetyPlanResponse)
async def update_plan(
    plan_id: int,
    payload: SafetyPlanUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await svc.update_plan(plan_id, current_user.id, payload, db)


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(
    plan_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await svc.delete_plan(plan_id, current_user.id, db)
