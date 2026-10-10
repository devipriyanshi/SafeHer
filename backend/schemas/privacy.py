from pydantic import BaseModel, field_validator


class PrivacySettingUpdate(BaseModel):
    location_access_enabled: bool | None = None
    location_sharing_enabled: bool | None = None
    store_journey_location: bool | None = None
    voice_assistance_enabled: bool | None = None
    include_location_in_alert: bool | None = None
    include_journey_details_in_alert: bool | None = None
    safety_event_retention_days: int | None = None
    auto_escalate_on_journey_expiry: bool | None = None
    voice_trigger_phrase: str | None = None

    @field_validator("safety_event_retention_days")
    @classmethod
    def valid_retention(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("Retention days cannot be negative")
        return v

    @field_validator("voice_trigger_phrase")
    @classmethod
    def phrase_not_empty(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("Voice trigger phrase cannot be empty")
        return v.strip() if v else v


class PrivacySettingResponse(BaseModel):
    location_access_enabled: bool
    location_sharing_enabled: bool
    store_journey_location: bool
    voice_assistance_enabled: bool
    include_location_in_alert: bool
    include_journey_details_in_alert: bool
    safety_event_retention_days: int
    auto_escalate_on_journey_expiry: bool
    voice_trigger_phrase: str

    model_config = {"from_attributes": True}


class PrivacySummaryItem(BaseModel):
    setting: str
    status: str
    description: str


class PrivacySummaryResponse(BaseModel):
    items: list[PrivacySummaryItem]
    data_collected: list[str]
    data_not_collected: list[str]
