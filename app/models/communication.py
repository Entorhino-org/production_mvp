"""
Communication models: Announcement, Feedback (anonymous), Alert.
"""

import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Boolean, DateTime, Integer, Text,
    ForeignKey, Enum as SAEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base
import enum


class AnnouncementTarget(str, enum.Enum):
    ALL = "all"
    TEACHERS = "teachers"
    STUDENTS = "students"
    PARENTS = "parents"


class AlertType(str, enum.Enum):
    PERFORMANCE_DROP = "performance_drop"
    FALLING_BEHIND = "falling_behind"
    HOMEWORK_MISSING = "homework_missing"
    HOMEWORK_POOR = "homework_poor"
    LOW_ATTENDANCE = "low_attendance"
    TEST_MISSING = "test_missing"
    NEW_TEST = "new_test"
    NEW_HOMEWORK = "new_homework"


class Announcement(Base):
    """School-wide or role-targeted announcement."""
    __tablename__ = "announcements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    author_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    target = Column(SAEnum(AnnouncementTarget), default=AnnouncementTarget.ALL)
    created_at = Column(DateTime, default=datetime.utcnow)

    author = relationship("User")


class Feedback(Base):
    """Student feedback about a teacher. Student_id stored for admin view but hidden from teacher."""
    __tablename__ = "feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    teacher_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    content = Column(Text, nullable=False)
    rating = Column(Integer, nullable=False)  # 1-5 stars
    created_at = Column(DateTime, default=datetime.utcnow)

    teacher = relationship("User", foreign_keys=[teacher_id])
    student = relationship("User", foreign_keys=[student_id])


class Alert(Base):
    """Smart alert sent to teachers/parents/admins."""
    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    recipient_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    alert_type = Column(SAEnum(AlertType), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("User", foreign_keys=[student_id])
    recipient = relationship("User", foreign_keys=[recipient_id])


class AnnouncementRead(Base):
    """Tracks which user has read which announcement."""
    __tablename__ = "announcement_reads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    announcement_id = Column(UUID(as_uuid=True), ForeignKey("announcements.id", ondelete="CASCADE"), nullable=False)
    read_at = Column(DateTime, default=datetime.utcnow)


class PushSubscription(Base):
    """Web Push notification subscription (VAPID)."""
    __tablename__ = "push_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    endpoint = Column(Text, nullable=False, unique=True)
    p256dh = Column(String(255), nullable=False)
    auth = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id])
