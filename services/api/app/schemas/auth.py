import uuid

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.user import EMAIL_PATTERN


class LoginRequest(BaseModel):
    email: str = Field(..., pattern=EMAIL_PATTERN)
    password: str = Field(..., min_length=6)


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., pattern=EMAIL_PATTERN)
    password: str = Field(..., min_length=8, max_length=128)
    farm_name: str | None = Field(None, min_length=1, max_length=100)
    locale: str = Field("en", pattern="^(en|fr|ar|ja)$")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    refresh_token: str


class FarmMembershipResponse(BaseModel):
    farm_id: uuid.UUID
    farm_name: str
    role: str

    model_config = ConfigDict(from_attributes=True)


class MeResponse(BaseModel):
    id: uuid.UUID
    email: str
    name: str
    locale: str
    memberships: list[FarmMembershipResponse]

    model_config = ConfigDict(from_attributes=True)
