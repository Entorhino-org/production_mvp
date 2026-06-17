"""
Models package — imports all models so Alembic and the app can discover them.
"""

from app.models.user import (
    User, UserRole, ParentStudentLink, OTPCode, OTPPurpose,
    JoinRequest, JoinRequestStatus, AITokenUsage, AISettings, GapAnalysis
)
from app.models.academic import (
    Class, Section, Subject, ClassSubject, TeacherAssignment,
    ClassStudent, Chapter, Topic, Test, TestResult, Attendance
)
from app.models.communication import (
    Announcement, AnnouncementTarget, Feedback, Alert, AlertType
)
from app.models.homework import Homework, HomeworkSubmission
from app.models.gaps import (
    QuizResponse, AssignmentSubmission, ComprehensionScore,
    EngagementEvent, TopicPrerequisite, StudentGap,
)

__all__ = [
    "User", "UserRole", "ParentStudentLink", "OTPCode", "OTPPurpose",
    "JoinRequest", "JoinRequestStatus", "AITokenUsage", "AISettings", "GapAnalysis",
    "Class", "Section", "Subject", "ClassSubject", "TeacherAssignment",
    "ClassStudent", "Chapter", "Topic", "Test", "TestResult", "Attendance",
    "Announcement", "AnnouncementTarget", "Feedback", "Alert", "AlertType",
    "Homework", "HomeworkSubmission",
    "QuizResponse", "AssignmentSubmission", "ComprehensionScore",
    "EngagementEvent", "TopicPrerequisite", "StudentGap",
]
