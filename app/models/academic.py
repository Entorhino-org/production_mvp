"""
Academic models: Class, Section, Subject, ClassSubject, TeacherAssignment,
ClassStudent, Topic, Test, TestResult, Attendance.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime, Integer, Date, Float, Text,
    ForeignKey, UniqueConstraint, JSON
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base


# ── School Structure ──────────────────────────────────────────

class Class(Base):
    """School class (e.g., '10th', '9th')."""
    __tablename__ = "classes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), unique=True, nullable=False)  # e.g., "10th"
    created_at = Column(DateTime, default=datetime.utcnow)

    sections = relationship("Section", back_populates="school_class", cascade="all, delete-orphan")
    class_subjects = relationship("ClassSubject", back_populates="school_class", cascade="all, delete-orphan")


class Section(Base):
    """Section within a class (e.g., 'A', 'B')."""
    __tablename__ = "sections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    class_id = Column(UUID(as_uuid=True), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(10), nullable=False)  # e.g., "A"
    created_at = Column(DateTime, default=datetime.utcnow)

    school_class = relationship("Class", back_populates="sections")
    students = relationship("ClassStudent", back_populates="section", cascade="all, delete-orphan")
    teacher_assignments = relationship("TeacherAssignment", back_populates="section", cascade="all, delete-orphan")
    join_requests = relationship("JoinRequest", back_populates="section")

    __table_args__ = (
        UniqueConstraint("class_id", "name", name="uq_class_section"),
    )


class Subject(Base):
    """School subject (e.g., 'Mathematics', 'Physics')."""
    __tablename__ = "subjects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    class_subjects = relationship("ClassSubject", back_populates="subject", cascade="all, delete-orphan")


class ClassSubject(Base):
    """Assigns a subject to a class (applies to all sections of that class)."""
    __tablename__ = "class_subjects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    class_id = Column(UUID(as_uuid=True), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)

    school_class = relationship("Class", back_populates="class_subjects")
    subject = relationship("Subject", back_populates="class_subjects")

    __table_args__ = (
        UniqueConstraint("class_id", "subject_id", name="uq_class_subject"),
    )


# ── Teacher ↔ Class/Section/Subject Assignment ───────────────

class TeacherAssignment(Base):
    """Assigns a teacher to a section+subject. is_class_teacher marks head teacher."""
    __tablename__ = "teacher_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    section_id = Column(UUID(as_uuid=True), ForeignKey("sections.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    is_class_teacher = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    teacher = relationship("User", back_populates="teacher_assignments")
    section = relationship("Section", back_populates="teacher_assignments")
    subject = relationship("Subject")

    __table_args__ = (
        UniqueConstraint("teacher_id", "section_id", "subject_id", name="uq_teacher_section_subject"),
    )


# ── Student ↔ Section ────────────────────────────────────────

class ClassStudent(Base):
    """Student enrolled in a section."""
    __tablename__ = "class_students"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    section_id = Column(UUID(as_uuid=True), ForeignKey("sections.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("User")
    section = relationship("Section", back_populates="students")

    __table_args__ = (
        UniqueConstraint("student_id", "section_id", name="uq_student_section"),
    )


# ── Chapters ─────────────────────────────────────────────────

class Chapter(Base):
    """Chapter groups topics — scoped per teacher + class + subject."""
    __tablename__ = "chapters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    class_id = Column(UUID(as_uuid=True), ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    teacher = relationship("User")
    school_class = relationship("Class")
    subject = relationship("Subject")

    __table_args__ = (
        UniqueConstraint("teacher_id", "class_id", "subject_id", "name", name="uq_teacher_class_subject_chapter"),
    )


# ── Topics (from OCR-extracted notes) ────────────────────────

class Topic(Base):
    """A topic created from uploaded class notes."""
    __tablename__ = "topics"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    section_id = Column(UUID(as_uuid=True), ForeignKey("sections.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    chapter_id = Column(UUID(as_uuid=True), ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False)
    extracted_text = Column(Text, nullable=True)
    image_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    section = relationship("Section")
    subject = relationship("Subject")
    teacher = relationship("User")
    chapter = relationship("Chapter")


# ── Tests ─────────────────────────────────────────────────────

class Test(Base):
    """Test based on a topic — AI asks questions during student test-taking."""
    __tablename__ = "tests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    section_id = Column(UUID(as_uuid=True), ForeignKey("sections.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(255), nullable=False)
    questions = Column(JSON, nullable=True)  # Can be empty — AI generates during test
    num_questions = Column(Integer, default=5)  # How many questions AI should ask
    input_mode = Column(String(20), default="both")  # "text", "voice", "both"
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    section = relationship("Section")
    subject = relationship("Subject")
    topic = relationship("Topic")


class TestResult(Base):
    """Student's answers and AI evaluation for a test."""
    __tablename__ = "test_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    test_id = Column(UUID(as_uuid=True), ForeignKey("tests.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    answers = Column(JSON, nullable=True)  # List of {question_index, answer_text, score, feedback}
    score = Column(Float, default=0.0)
    mode = Column(String(10), default="text")  # "text" or "voice"
    topic_analysis = Column(JSON, nullable=True)  # {weak_topics: [], strong_topics: []}
    taken_at = Column(DateTime, default=datetime.utcnow)

    test = relationship("Test")
    student = relationship("User")

    __table_args__ = (
        UniqueConstraint("test_id", "student_id", name="uq_test_student"),
    )


# ── Attendance ────────────────────────────────────────────────

class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    section_id = Column(UUID(as_uuid=True), ForeignKey("sections.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    present = Column(Boolean, default=True)

    student = relationship("User")
    section = relationship("Section")

    __table_args__ = (
        UniqueConstraint("student_id", "section_id", "date", name="uq_student_section_date"),
    )
