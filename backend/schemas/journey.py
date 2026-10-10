from pydantic import BaseModel, field_validator
from datetime import datetime
from backend.models.journey import JourneyStatus


class JourneyStartRequest(BaseModel):
    origin: str
    destination: str
    expected_duration_minutes: int
    safety_plan_id: int | None = None

    @field_validator("origin", "destination")
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


class JourneyExtendRequest(BaseModel):
    extend_by_minutes: int

    @field_validator("extend_by_minutes")
    @classmethod
    def positive_extension(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Extension must be greater than 0")
        return v


class LocationUpdate(BaseModel):
    latitude: float
    longitude: float


class JourneyResponse(BaseModel):
    id: int
    origin: str
    destination: str
    expected_duration_minutes: int
    started_at: datetime
    expected_arrival_at: datetime
    completed_at: datetime | None
    status: JourneyStatus
    extension_count: int
    safety_plan_id: int | None
    last_latitude: float | None
    last_longitude: float | None

    model_config = {"from_attributes": True}


class TimelineEvent(BaseModel):
    timestamp: datetime
    event: str
    detail: str | None = None


class JourneyTimelineResponse(BaseModel):
    journey_id: int
    status: JourneyStatus
    timeline: list[TimelineEvent]
