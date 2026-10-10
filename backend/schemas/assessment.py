from pydantic import BaseModel
from datetime import datetime
from backend.models.assessment import SafetyIndication


class AssessmentResponse(BaseModel):
    id: int
    journey_id: int
    indication: SafetyIndication
    assistance_score: float
    explanation: str
    suggested_action: str
    contributing_signal_ids: list[int]
    ai_available: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalyzeRequest(BaseModel):
    journey_id: int
