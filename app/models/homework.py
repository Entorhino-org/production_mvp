"""
Homework models: Homework, HomeworkSubmission.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, DateTime, Float, Text, ForeignKey
)
# submission_type values: "photo", "text", "both"
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


class Homework(Base):
    """Homework assigned by a teacher to a section."""
    __tablename__ = "homework"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    section_id = Column(UUID(as_uuid=True), ForeignKey("sections.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    chapter_id = Column(UUID(as_uuid=True), ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(DateTime, nullable=False)
    submission_type = Column(String(20), default="both")  # "photo", "text", "both"
    created_at = Column(DateTime, default=datetime.utcnow)

    section = relationship("Section")
    subject = relationship("Subject")
    teacher = relationship("User")
    chapter = relationship("Chapter")


class HomeworkSubmission(Base):
    """Student's homework submission with AI-checked results."""
    __tablename__ = "homework_submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    homework_id = Column(UUID(as_uuid=True), ForeignKey("homework.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    image_path = Column(String(500), nullable=True)
    text_content = Column(Text, nullable=True)  # Typed text submission
    extracted_text = Column(Text, nullable=True)  # Exact OCR output from image
    ai_feedback = Column(Text, nullable=True)
    score = Column(Float, nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow)

    homework = relationship("Homework")
    student = relationship("User")
