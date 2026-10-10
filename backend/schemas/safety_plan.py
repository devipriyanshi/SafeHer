from pydantic import BaseModel, field_validator
from datetime import datetime


class SafetyPlanCreate(BaseModel):
    name: str
    origin: str
    destination: str
    expected_duration_minutes: int
    notes: str | None = None

    @field_validator("name", "origin", "destination")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()

    @field_validator("expected_duration_minutes")
    @classmethod
    def positive_duration(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Duration must be greater than 0")
        return v


class SafetyPlanUpdate(BaseModel):
    name: str | None = None
    origin: str | None = None
    destination: str | None = None
    expected_duration_minutes: int | None = None
    notes: str | None = None
    is_active: bool | None = None


class SafetyPlanResponse(BaseModel):
    id: int
    name: str
    origin: str
    destination: str
    expected_duration_minutes: int
    notes: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}
