"""
Auth schemas — registration, login, OTP, tokens.
"""

from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from app.models.user import UserRole
import re


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: Optional[str] = None
    role: UserRole

    # Teacher-specific
    subjects: Optional[list[str]] = None  # subject names for multi-select

    # Parent-specific
    relationship_type: Optional[str] = None  # father, mother, guardian

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one digit")
        return v


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    code: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: "UserBasic"


class RefreshRequest(BaseModel):
    refresh_token: str


class ResendOTPRequest(BaseModel):
    email: EmailStr


class UserBasic(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    is_email_verified: bool
    is_approved: bool

    class Config:
        from_attributes = True


# Update forward ref
TokenResponse.model_rebuild()
