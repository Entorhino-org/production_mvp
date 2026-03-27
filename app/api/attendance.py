"""
Attendance API — mark and view attendance.
"""

from datetime import date, datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.user import User, UserRole
from app.models.academic import Attendance, ClassStudent, TeacherAssignment, Section, Class
from app.schemas.academic import AttendanceMarkRequest
from app.core.dependencies import get_current_user
from app.services.analytics import check_and_create_alerts

router = APIRouter(prefix="/api/attendance", tags=["Attendance"])


@router.post("/mark")
async def mark_attendance(
    req: AttendanceMarkRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Class teacher marks attendance for a section on a given date."""
    if current_user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Only teachers can mark attendance")

    # Verify teacher is class teacher for this section (or admin)
    if current_user.role == UserRole.TEACHER:
        result = await db.execute(
            select(TeacherAssignment).where(
                TeacherAssignment.teacher_id == current_user.id,
                TeacherAssignment.section_id == req.section_id,
                TeacherAssignment.is_class_teacher == True,
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="You are not the class teacher for this section")

    att_date = date.fromisoformat(req.date)

    for record in req.records:
        # Upsert attendance
        result = await db.execute(
            select(Attendance).where(
                Attendance.student_id == record.student_id,
                Attendance.section_id == req.section_id,
                Attendance.date == att_date,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.present = record.present
        else:
            db.add(Attendance(
                student_id=record.student_id,
                section_id=req.section_id,
                date=att_date,
                present=record.present,
            ))

        # Check alerts for low attendance
        if not record.present:
            await check_and_create_alerts(db, record.student_id)

    await db.flush()
    return {"message": f"Attendance marked for {len(req.records)} students"}


@router.get("/section/{section_id}")
async def get_section_attendance(
    section_id: str,
    att_date: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get attendance for a section on a given date (default: today)."""
    target_date = date.fromisoformat(att_date) if att_date else date.today()

    # Get students in this section
    result = await db.execute(
        select(ClassStudent, User)
        .join(User, ClassStudent.student_id == User.id)
        .where(ClassStudent.section_id == section_id)
        .order_by(User.full_name)
    )
    students = result.all()

    # Get attendance records for this date
    attendance_result = await db.execute(
        select(Attendance).where(
            Attendance.section_id == section_id,
            Attendance.date == target_date,
        )
    )
    attendance_map = {str(a.student_id): a.present for a in attendance_result.scalars().all()}

    return [
        {
            "student_id": str(cs.student_id),
            "student_name": u.full_name,
            "date": target_date.isoformat(),
            "present": attendance_map.get(str(cs.student_id), None),  # None = not yet marked
        }
        for cs, u in students
    ]


@router.get("/student/{student_id}")
async def get_student_attendance(
    student_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get attendance history for a student (for parent/student/teacher view)."""
    # Parents can only see their children
    if current_user.role == UserRole.PARENT:
        from app.models.user import ParentStudentLink
        result = await db.execute(
            select(ParentStudentLink).where(
                ParentStudentLink.parent_id == current_user.id,
                ParentStudentLink.student_id == student_id,
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Not authorized to view this student")

    # Students can only see their own
    if current_user.role == UserRole.STUDENT and str(current_user.id) != student_id:
        raise HTTPException(status_code=403, detail="You can only view your own attendance")

    result = await db.execute(
        select(Attendance)
        .where(Attendance.student_id == student_id)
        .order_by(Attendance.date.desc())
        .limit(90)
    )
    return [
        {
            "date": a.date.isoformat(),
            "present": a.present,
            "section_id": str(a.section_id),
        }
        for a in result.scalars().all()
    ]


@router.get("/section/{section_id}/history")
async def get_section_attendance_history(
    section_id: str,
    days: int = Query(default=30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get attendance summary (present/absent counts per date) for a section over N days.
    Returns one row per date — uses SQL GROUP BY for aggregation."""
    from sqlalchemy import case, literal

    if current_user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Only teachers/admin")

    start_date = date.today() - timedelta(days=days)

    # Count students in section (1 query)
    cs_result = await db.execute(
        select(func.count()).select_from(ClassStudent).where(ClassStudent.section_id == section_id)
    )
    total_students = cs_result.scalar() or 0

    # SQL aggregation — 1 query instead of loading all records
    agg_result = await db.execute(
        select(
            Attendance.date,
            func.sum(case((Attendance.present == True, literal(1)), else_=literal(0))).label("present"),
            func.sum(case((Attendance.present == False, literal(1)), else_=literal(0))).label("absent"),
            func.count(Attendance.id).label("total"),
        )
        .where(
            Attendance.section_id == section_id,
            Attendance.date >= start_date,
        )
        .group_by(Attendance.date)
        .order_by(Attendance.date.desc())
    )

    return {
        "total_students": total_students,
        "history": [
            {"date": row.date.isoformat(), "present": row.present, "absent": row.absent, "total": row.total}
            for row in agg_result.all()
        ],
    }
