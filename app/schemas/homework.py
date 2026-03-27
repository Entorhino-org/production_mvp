"""
Homework schemas.
"""

from pydantic import BaseModel
from typing import Optional


class HomeworkCreate(BaseModel):
    section_id: str
    subject_id: str
    title: str
    description: Optional[str] = None
    due_date: str  # ISO datetime
    submission_type: str = "both"  # "photo", "text", "both"


class HomeworkResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    section_id: str
    subject_id: str
    subject_name: Optional[str] = None
    teacher_name: Optional[str] = None
    due_date: Optional[str] = None
    created_at: Optional[str] = None


class HomeworkSubmissionResponse(BaseModel):
    id: str
    homework_id: str
    student_id: str
    student_name: Optional[str] = None
    image_path: Optional[str] = None
    ai_feedback: Optional[str] = None
    score: Optional[float] = None
    submitted_at: Optional[str] = None
