"""
User schemas — profile, student onboarding, parent linking.
"""

from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID


class StudentProfileUpdate(BaseModel):
    """Step 2 after email verification — student fills additional details."""
    admission_number: str
    guardian_name: str
    guardian_phone: str


class TeacherProfileUpdate(BaseModel):
    """Step 2 after email verification — teacher fills additional details."""
    employee_id: str
    department: str


class ParentLinkRequest(BaseModel):
    """Parent enters student's email to initiate linking."""
    student_email: EmailStr


class ParentLinkVerify(BaseModel):
    """Parent enters OTP sent to student's email."""
    student_email: EmailStr
    code: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    phone: Optional[str] = None
    role: str
    is_email_verified: bool
    is_approved: bool
    admission_number: Optional[str] = None
    guardian_name: Optional[str] = None
    guardian_phone: Optional[str] = None
    employee_id: Optional[str] = None
    department: Optional[str] = None
    relationship_type: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class JoinRequestCreate(BaseModel):
    """Student/teacher requests to join a section."""
    section_id: str


class JoinRequestResponse(BaseModel):
    id: str
    user_id: str
    user_name: str
    user_email: str
    user_role: str
    section_id: Optional[str] = None
    section_name: Optional[str] = None
    class_name: Optional[str] = None
    status: str
    created_at: Optional[str] = None


class JoinRequestAction(BaseModel):
    """Approve or reject a join request."""
    status: str  # approved / rejected
