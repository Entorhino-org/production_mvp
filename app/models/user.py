"""
User-related database models: User, OTPCode, ParentStudentLink, AITokenUsage, AISettings.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime, Integer, Date,
    ForeignKey, Enum as SAEnum, Text, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
import enum


# ── Enums ─────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    SCHOOL_ADMIN = "school_admin"
    TEACHER = "teacher"
    STUDENT = "student"
    PARENT = "parent"


class OTPPurpose(str, enum.Enum):
    EMAIL_VERIFY = "email_verify"
    PARENT_LINK = "parent_link"


class JoinRequestStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


# ── User ──────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(20), nullable=True)
    role = Column(SAEnum(UserRole), nullable=False)
    is_email_verified = Column(Boolean, default=False)
    is_approved = Column(Boolean, default=False)  # Admin/class-teacher approval

    # Student-specific fields
    admission_number = Column(String(50), nullable=True)
    guardian_name = Column(String(255), nullable=True)
    guardian_phone = Column(String(20), nullable=True)

    # Teacher-specific fields
    employee_id = Column(String(50), nullable=True)
    department = Column(String(100), nullable=True)
    # teacher_subjects stored as comma-separated or via relationship

    # Parent-specific fields
    relationship_type = Column(String(20), nullable=True)  # father, mother, guardian

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    children = relationship(
        "User",
        secondary="parent_student_links",
        primaryjoin="User.id == ParentStudentLink.parent_id",
        secondaryjoin="User.id == ParentStudentLink.student_id",
        backref="parents",
        lazy="selectin",
    )
    join_requests = relationship("JoinRequest", back_populates="user", foreign_keys="JoinRequest.user_id")
    teacher_assignments = relationship("TeacherAssignment", back_populates="teacher")


# ── Parent–Student Link ──────────────────────────────────────

class ParentStudentLink(Base):
    __tablename__ = "parent_student_links"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("parent_id", "student_id", name="uq_parent_student"),
    )


# ── OTP Codes ────────────────────────────────────────────────

class OTPCode(Base):
    __tablename__ = "otp_codes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, index=True)
    code = Column(String(6), nullable=False)
    purpose = Column(SAEnum(OTPPurpose), nullable=False, default=OTPPurpose.EMAIL_VERIFY)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Join Requests ────────────────────────────────────────────

class JoinRequest(Base):
    __tablename__ = "join_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    section_id = Column(UUID(as_uuid=True), ForeignKey("sections.id", ondelete="CASCADE"), nullable=True)
    status = Column(SAEnum(JoinRequestStatus), default=JoinRequestStatus.PENDING)
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="join_requests", foreign_keys=[user_id])
    reviewer = relationship("User", foreign_keys=[reviewed_by])
    section = relationship("Section", back_populates="join_requests")


# ── AI Token Usage ───────────────────────────────────────────

class AITokenUsage(Base):
    __tablename__ = "ai_token_usage"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tokens_used = Column(Integer, default=0)
    date = Column(Date, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_user_date_tokens"),
    )


# ── AI Settings (singleton-ish) ──────────────────────────────

class AISettings(Base):
    __tablename__ = "ai_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    daily_student_limit = Column(Integer, default=5000)
    daily_teacher_limit = Column(Integer, default=15000)
    # AI models
    ai_model = Column(String(200), default="google/gemini-2.0-flash-001")
    ocr_model = Column(String(200), default="google/gemini-2.0-flash-001")
    evaluation_model = Column(String(200), default="google/gemini-2.0-flash-001")
    # Email / OTP
    otp_sender_email = Column(String(200), default="")
    otp_sender_password = Column(String(200), default="")
    smtp_host = Column(String(200), default="smtp.gmail.com")
    smtp_port = Column(Integer, default=587)
    # School
    school_name = Column(String(200), default="My School")
    # Resend email API
    resend_api_key = Column(String(500), default="")
    resend_from_email = Column(String(200), default="")
    # Gap analysis thresholds
    gap_test_threshold = Column(Integer, default=60)      # trigger gap analysis for test scores below this
    gap_homework_threshold = Column(Integer, default=50)   # trigger gap analysis for homework scores below this
    # OpenRouter
    openrouter_api_key = Column(String(500), default="")
    openai_api_key = Column(String(500), default="")
    # Gemini (for Live API voice interviews)
    gemini_api_key = Column(String(500), default="")
    # Sarvam AI (OCR / Document Intelligence)
    sarvam_api_key = Column(String(500), default="")
    sarvam_stt_model = Column(String(200), default="saaras:v3")
    # Voice Interview VAD settings
    vad_silence_ms = Column(Integer, default=2000)
    vad_sensitivity = Column(String(50), default="END_SENSITIVITY_HIGH")
    vad_proactivity = Column(Boolean, default=False)


# ── API Keys (multiple per provider, round-robin) ────────────

class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider = Column(String(50), nullable=False)  # "openrouter" or "openai"
    api_key = Column(String(500), nullable=False)
    label = Column(String(100), default="")
    error_count = Column(Integer, default=0)
    last_error = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Gap Analysis ─────────────────────────────────────────────

class GapAnalysis(Base):
    """AI-detected concept gap for a student based on test/homework performance."""
    __tablename__ = "gap_analysis"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("topics.id", ondelete="SET NULL"), nullable=True)
    chapter_id = Column(UUID(as_uuid=True), ForeignKey("chapters.id", ondelete="SET NULL"), nullable=True)
    concept = Column(String(255), nullable=False)  # e.g. "Fractions", "Quadratic Equations"
    description = Column(Text, nullable=False)  # What the student is struggling with
    suggestion = Column(Text, nullable=False)  # How to improve
    severity = Column(String(20), default="moderate")  # minor / moderate / critical
    source = Column(String(20), nullable=False)  # "test" or "homework"
    source_id = Column(UUID(as_uuid=True), nullable=True)  # TestResult or HomeworkSubmission ID
    status = Column(String(20), default="open")  # open / resolved
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("User", foreign_keys=[student_id])
    subject = relationship("Subject")
    topic = relationship("Topic")
    chapter = relationship("Chapter")
