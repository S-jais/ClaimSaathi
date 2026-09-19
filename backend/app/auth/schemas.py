"""
app/auth/schemas.py
Pydantic request/response schemas for auth endpoints.
All data crossing the API boundary is validated here.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, model_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str | None = Field(None, max_length=255)

    @model_validator(mode="after")
    def password_strength(self) -> "RegisterRequest":
        pwd = self.password
        if not any(c.isupper() for c in pwd):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in pwd):
            raise ValueError("Password must contain at least one digit")
        if not any(c in "@#$%!^&*" for c in pwd):
            raise ValueError("Password must contain at least one special character (@#$%!^&*)")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str | None
    roles: list[str]
    mfa_enabled: bool
    is_demo: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class LogoutRequest(BaseModel):
    refresh_token: str
