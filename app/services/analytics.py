"""
Analytics service — aggregation logic for dashboards and smart alerts.
"""

from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
import logging

logger = logging.getLogger(__name__)

from app.models.academic import TestResult, Test, Attendance, ClassStudent
from app.models.homework import HomeworkSubmission, Homework
from app.models.communication import Alert, AlertType
from app.models.user import User, UserRole, ParentStudentLink


async def get_student_performance(db: AsyncSession, student_id: UUID) -> dict:
    """Get comprehensive performance data for a student."""
    # Average score across all tests
    result = await db.execute(
        select(func.avg(TestResult.score), func.count(TestResult.id))
        .where(TestResult.student_id == student_id)
    )
    row = result.one()
    avg_score = float(row[0] or 0)
    total_tests = row[1]

    # Recent test results (last 10)
    result = await db.execute(
        select(TestResult, Test)
        .join(Test, TestResult.test_id == Test.id)
        .where(TestResult.student_id == student_id)
        .order_by(TestResult.taken_at.desc())
        .limit(10)
    )
    recent_tests = []
    for tr, t in result.all():
        recent_tests.append({
            "test_title": t.title,
            "score": tr.score,
            "mode": tr.mode or "text",
            "taken_at": tr.taken_at.isoformat() if tr.taken_at else None,
            "topic_analysis": tr.topic_analysis,
            "answers": tr.answers,
        })

    # Attendance rate (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    result = await db.execute(
        select(
            func.count(Attendance.id).filter(Attendance.present == True),
            func.count(Attendance.id),
        ).where(
            Attendance.student_id == student_id,
            Attendance.date >= thirty_days_ago.date(),
        )
    )
    att_row = result.one()
    present_count = att_row[0]
    total_days = att_row[1]
    attendance_rate = (present_count / total_days * 100) if total_days > 0 else 0

    # Homework completion
    result = await db.execute(
        select(func.avg(HomeworkSubmission.score), func.count(HomeworkSubmission.id))
        .where(HomeworkSubmission.student_id == student_id)
    )
    hw_row = result.one()

    # Recent homework submissions (last 10)
    result = await db.execute(
        select(HomeworkSubmission, Homework)
        .join(Homework, HomeworkSubmission.homework_id == Homework.id)
        .where(HomeworkSubmission.student_id == student_id)
        .order_by(HomeworkSubmission.submitted_at.desc())
        .limit(10)
    )
    recent_homework = []
    for hs, hw in result.all():
        recent_homework.append({
            "title": hw.title,
            "score": hs.score,
            "ai_feedback": hs.ai_feedback,
            "extracted_text": hs.extracted_text,
            "submitted_at": hs.submitted_at.isoformat() if hs.submitted_at else None,
        })

    return {
        "average_score": round(avg_score, 1),
        "total_tests_taken": total_tests,
        "recent_tests": recent_tests,
        "recent_homework": recent_homework,
        "attendance_rate": round(attendance_rate, 1),
        "attendance_present": present_count,
        "attendance_total": total_days,
        "homework_average": round(float(hw_row[0] or 0), 1),
        "homework_submitted": hw_row[1],
    }


async def check_and_create_alerts(db: AsyncSession, student_id: UUID):
    """Check if a student needs smart alerts and create them."""
    perf = await get_student_performance(db, student_id)

    alerts_to_create = []

    # Alert: Performance drop (average below 40)
    if perf["total_tests_taken"] >= 2 and perf["average_score"] < 40:
        alerts_to_create.append({
            "alert_type": AlertType.PERFORMANCE_DROP,
            "message": f"Student's average score has dropped to {perf['average_score']}%. Immediate attention needed.",
        })

    # Alert: Low attendance (below 75%)
    if perf["attendance_total"] >= 5 and perf["attendance_rate"] < 75:
        alerts_to_create.append({
            "alert_type": AlertType.LOW_ATTENDANCE,
            "message": f"Student's attendance is at {perf['attendance_rate']}% (last 30 days). Below minimum threshold.",
        })

    if not alerts_to_create:
        return

    # Bulk: get all recipients (parents + class teachers) in 2 queries
    recipient_ids = []

    # Parents (1 query)
    result = await db.execute(
        select(ParentStudentLink.parent_id).where(ParentStudentLink.student_id == student_id)
    )
    recipient_ids.extend([r[0] for r in result.all()])

    # Class teachers — bulk via JOIN (1 query instead of loop)
    from app.models.academic import TeacherAssignment
    result = await db.execute(
        select(TeacherAssignment.teacher_id)
        .join(ClassStudent, ClassStudent.section_id == TeacherAssignment.section_id)
        .where(
            ClassStudent.student_id == student_id,
            TeacherAssignment.is_class_teacher == True,
        )
    )
    recipient_ids.extend([r[0] for r in result.all()])

    unique_recipients = list(set(recipient_ids))
    if not unique_recipients:
        return

    # Bulk: check existing unread alerts (1 query)
    alert_types = [a["alert_type"] for a in alerts_to_create]
    existing_result = await db.execute(
        select(Alert.alert_type, Alert.recipient_id).where(
            Alert.student_id == student_id,
            Alert.alert_type.in_(alert_types),
            Alert.is_read == False,
        )
    )
    existing_set = {(at, rid) for at, rid in existing_result.all()}

    # Create alerts for each recipient
    push_targets = []
    for alert_data in alerts_to_create:
        for recipient_id in unique_recipients:
            if (alert_data["alert_type"], recipient_id) not in existing_set:
                db.add(Alert(
                    student_id=student_id,
                    recipient_id=recipient_id,
                    alert_type=alert_data["alert_type"],
                    message=alert_data["message"],
                ))
                push_targets.append((recipient_id, alert_data["message"]))

    await db.flush()

    # Send web push for created alerts
    if push_targets:
        try:
            from app.api.push import send_push_to_user
            for recipient_id, message in push_targets:
                await send_push_to_user(db, recipient_id, "🚨 Alert", message[:200], "/dashboard")
        except Exception as e:
            logger.warning(f"[PUSH] Alert push failed: {e}")
