from pydantic import BaseModel
from datetime import datetime
from backend.models.emergency import EmergencyEventType, EmergencyEventStatus


class SOSRequest(BaseModel):
    event_type: EmergencyEventType = EmergencyEventType.MANUAL_SOS
    latitude: float | None = None
    longitude: float | None = None
    notes: str | None = None
    journey_id: int | None = None


class EmergencyEventResponse(BaseModel):
    id: int
    event_type: EmergencyEventType
    status: EmergencyEventStatus
    latitude: float | None
    longitude: float | None
    location_link: str | None
    notes: str | None
    notifications_sent: bool
    created_at: datetime
    resolved_at: datetime | None
    journey_id: int | None

    model_config = {"from_attributes": True}


class NotificationLogResponse(BaseModel):
    id: int
    channel: str
    recipient: str
    success: bool
    error_message: str | None
    sent_at: datetime

    model_config = {"from_attributes": True}


class EmergencyDetailResponse(EmergencyEventResponse):
    notification_logs: list[NotificationLogResponse] = []
