"""
Communication schemas — announcements, feedback, alerts.
"""

from pydantic import BaseModel
from typing import Optional
from app.models.communication import AnnouncementTarget


class AnnouncementCreate(BaseModel):
    title: str
    content: str
    target: str = "all"


class AnnouncementResponse(BaseModel):
    id: str
    title: str
    content: str
    target: str
    author_name: Optional[str] = None
    created_at: Optional[str] = None


class FeedbackCreate(BaseModel):
    teacher_id: str
    content: str
    rating: int  # 1-5


class FeedbackResponse(BaseModel):
    id: str
    teacher_id: str
    teacher_name: Optional[str] = None
    content: str
    rating: int
    created_at: Optional[str] = None


class AlertResponse(BaseModel):
    id: str
    student_id: str
    student_name: Optional[str] = None
    alert_type: str
    message: str
    is_read: bool
    created_at: Optional[str] = None
