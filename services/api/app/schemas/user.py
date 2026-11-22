import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class UserBase(BaseModel):
    email: str = Field(..., pattern=EMAIL_PATTERN, max_length=254)
    name: str = Field(..., min_length=1, max_length=100)
    locale: str = Field("en", pattern="^(en|fr|ar|ja)$")


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)


class UserUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    locale: Optional[str] = Field(None, pattern="^(en|fr|ar|ja)$")


class UserResponse(UserBase):
    id: uuid.UUID
    created_at: datetime
    disabled_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
