from pydantic import BaseModel, EmailStr, field_validator


class ContactCreate(BaseModel):
    name: str
    phone: str | None = None
    email: EmailStr | None = None
    relationship: str
    is_primary: bool = False

    @field_validator("name", "relationship")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()

    @field_validator("phone", "email", mode="before")
    @classmethod
    def at_least_one_contact(cls, v):
        return v

    def model_post_init(self, __context) -> None:
        if not self.phone and not self.email:
            raise ValueError("At least one of phone or email must be provided")


class ContactUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    relationship: str | None = None
    is_primary: bool | None = None
    is_active: bool | None = None


class ContactResponse(BaseModel):
    id: int
    name: str
    phone: str | None
    email: str | None
    relationship: str
    is_primary: bool
    is_active: bool

    model_config = {"from_attributes": True}
