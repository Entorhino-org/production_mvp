"""
Academic schemas — classes, sections, subjects, topics, tests, attendance.
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime, date


# ── Classes & Sections ───────────────────────────────────────

class ClassCreate(BaseModel):
    name: str


class ClassResponse(BaseModel):
    id: str
    name: str
    sections: list["SectionResponse"] = []

    class Config:
        from_attributes = True


class SectionCreate(BaseModel):
    name: str
    class_id: str


class SectionResponse(BaseModel):
    id: str
    name: str
    class_id: str
    class_name: Optional[str] = None

    class Config:
        from_attributes = True


# ── Subjects ──────────────────────────────────────────────────

class SubjectCreate(BaseModel):
    name: str


class SubjectResponse(BaseModel):
    id: str
    name: str

    class Config:
        from_attributes = True


class ClassSubjectAssign(BaseModel):
    class_id: str
    subject_id: str


# ── Teacher Assignment ───────────────────────────────────────

class TeacherAssignmentCreate(BaseModel):
    teacher_id: str
    section_id: str
    subject_id: str
    is_class_teacher: bool = False


class TeacherAssignmentResponse(BaseModel):
    id: str
    teacher_id: str
    teacher_name: Optional[str] = None
    section_id: str
    section_name: Optional[str] = None
    class_name: Optional[str] = None
    subject_id: str
    subject_name: Optional[str] = None
    is_class_teacher: bool

    class Config:
        from_attributes = True


# ── Topics ────────────────────────────────────────────────────

class TopicResponse(BaseModel):
    id: str
    title: str
    extracted_text: Optional[str] = None
    section_id: str
    subject_id: str
    subject_name: Optional[str] = None
    created_at: Optional[str] = None


# ── Tests ─────────────────────────────────────────────────────

class TestCreate(BaseModel):
    topic_id: str
    title: str
    num_questions: int = 5
    due_date: Optional[str] = None
    input_mode: str = "both"  # "text", "voice", "both"


class TestResponse(BaseModel):
    id: str
    title: str
    questions: list[dict] = []
    section_id: str
    subject_id: str
    subject_name: Optional[str] = None
    due_date: Optional[str] = None
    created_at: Optional[str] = None


class SubmitAnswerRequest(BaseModel):
    """Student submits an answer for a single question."""
    question_index: int
    answer_text: str


class SubmitTestRequest(BaseModel):
    """Student submits all answers for a test."""
    answers: list[SubmitAnswerRequest]


class TestResultResponse(BaseModel):
    id: str
    test_id: str
    test_title: Optional[str] = None
    student_id: str
    score: float
    answers: list[dict] = []
    topic_analysis: Optional[dict] = None
    taken_at: Optional[str] = None


# ── Attendance ────────────────────────────────────────────────

class AttendanceMarkRequest(BaseModel):
    section_id: str
    date: str  # YYYY-MM-DD
    records: list["AttendanceRecord"]


class AttendanceRecord(BaseModel):
    student_id: str
    present: bool


class AttendanceResponse(BaseModel):
    student_id: str
    student_name: str
    date: str
    present: bool


# Rebuild forward refs
ClassResponse.model_rebuild()
AttendanceMarkRequest.model_rebuild()
