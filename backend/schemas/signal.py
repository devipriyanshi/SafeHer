from pydantic import BaseModel
from datetime import datetime
from backend.models.signal import SignalType, SignalSeverity


class SignalCreateRequest(BaseModel):
    journey_id: int
    signal_type: SignalType
    severity: SignalSeverity = SignalSeverity.LOW
    description: str


class SignalResponse(BaseModel):
    id: int
    journey_id: int
    signal_type: SignalType
    severity: SignalSeverity
    description: str
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}
