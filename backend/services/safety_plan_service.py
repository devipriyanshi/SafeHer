from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status

from backend.models.safety_plan import SafetyPlan
from backend.schemas.safety_plan import SafetyPlanCreate, SafetyPlanUpdate


async def get_user_plans(user_id: int, db: AsyncSession) -> list[SafetyPlan]:
    result = await db.execute(
        select(SafetyPlan)
        .where(SafetyPlan.user_id == user_id)
        .order_by(SafetyPlan.created_at.desc())
    )
    return list(result.scalars().all())


async def get_plan_or_403(plan_id: int, user_id: int, db: AsyncSession) -> SafetyPlan:
    result = await db.execute(select(SafetyPlan).where(SafetyPlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Safety plan not found")
    if plan.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return plan


async def create_plan(user_id: int, payload: SafetyPlanCreate, db: AsyncSession) -> SafetyPlan:
    plan = SafetyPlan(user_id=user_id, **payload.model_dump())
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


async def update_plan(plan_id: int, user_id: int, payload: SafetyPlanUpdate, db: AsyncSession) -> SafetyPlan:
    plan = await get_plan_or_403(plan_id, user_id, db)
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(plan, field, value)
    await db.commit()
    await db.refresh(plan)
    return plan


async def delete_plan(plan_id: int, user_id: int, db: AsyncSession) -> None:
    plan = await get_plan_or_403(plan_id, user_id, db)
    await db.delete(plan)
    await db.commit()
