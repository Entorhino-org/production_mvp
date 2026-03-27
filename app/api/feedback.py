"""
Feedback API — student rates teacher, admin sees all, teacher sees own (anonymous).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.user import User, UserRole
from app.models.communication import Feedback
from app.models.academic import ClassStudent, TeacherAssignment, Section, Class, Subject
from app.schemas.communication import FeedbackCreate
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/api/feedback", tags=["Feedback"])


@router.get("/my-teachers")
async def get_my_teachers(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get teachers who teach in the student's class/section — for feedback dropdown."""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students can access this")

    # Get the student's enrolled sections
    enrolled = await db.execute(
        select(ClassStudent.section_id).where(ClassStudent.student_id == current_user.id)
    )
    section_ids = [r[0] for r in enrolled.all()]
    if not section_ids:
        return []

    # Get teachers assigned to those sections
    result = await db.execute(
        select(TeacherAssignment, User, Subject)
        .join(User, TeacherAssignment.teacher_id == User.id)
        .join(Subject, TeacherAssignment.subject_id == Subject.id)
        .where(TeacherAssignment.section_id.in_(section_ids))
    )

    seen = set()
    teachers = []
    for ta, u, s in result.all():
        key = str(u.id)
        if key not in seen:
            seen.add(key)
            teachers.append({
                "id": key,
                "full_name": u.full_name,
                "subject": s.name,
            })

    return teachers


@router.post("/", status_code=201)
async def submit_feedback(
    req: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit feedback about a teacher. Only students can submit."""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students can submit feedback")

    if req.rating < 1 or req.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")

    # Verify teacher exists
    result = await db.execute(select(User).where(User.id == req.teacher_id, User.role == UserRole.TEACHER))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Teacher not found")

    # Check if already submitted feedback for this teacher today
    from datetime import datetime, timedelta
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    existing = await db.execute(
        select(Feedback).where(
            Feedback.student_id == current_user.id,
            Feedback.teacher_id == req.teacher_id,
            Feedback.created_at >= today_start,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="You have already submitted feedback for this teacher today")

    # Store student_id for admin visibility (hidden from teacher view)
    feedback = Feedback(
        teacher_id=req.teacher_id,
        student_id=current_user.id,
        content=req.content,
        rating=req.rating,
    )
    db.add(feedback)
    await db.flush()
    return {"message": "Feedback submitted successfully"}


@router.get("/teacher/{teacher_id}")
async def get_teacher_feedback(
    teacher_id: str,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """View feedback for a teacher. Teacher sees own (no names). Admin sees all (with names).
    Paginated with limit/offset. Uses single JOIN for student names."""
    if current_user.role == UserRole.TEACHER and str(current_user.id) != teacher_id:
        raise HTTPException(status_code=403, detail="You can only view your own feedback")
    if current_user.role not in (UserRole.ADMIN, UserRole.TEACHER):
        raise HTTPException(status_code=403, detail="Not authorized")

    limit = min(max(limit, 1), 100)

    # Single query with LEFT JOIN for student names (avoids N+1)
    result = await db.execute(
        select(Feedback, User)
        .join(User, Feedback.student_id == User.id, isouter=True)
        .where(Feedback.teacher_id == teacher_id)
        .order_by(Feedback.created_at.desc())
        .offset(offset).limit(limit)
    )
    rows = result.all()

    # Calculate average (1 query)
    avg_result = await db.execute(
        select(func.avg(Feedback.rating), func.count(Feedback.id))
        .where(Feedback.teacher_id == teacher_id)
    )
    agg = avg_result.one()

    items = []
    for f, student in rows:
        item = {
            "id": str(f.id),
            "content": f.content,
            "rating": f.rating,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        }
        # Only admin sees who gave the feedback
        if current_user.role == UserRole.ADMIN and student:
            item["student_name"] = student.full_name
        items.append(item)

    return {
        "average_rating": round(float(agg[0] or 0), 1),
        "total_reviews": agg[1],
        "feedback": items,
    }
