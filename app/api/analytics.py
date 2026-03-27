"""
Analytics API — student performance dashboard, class-level insights.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime

from app.database import get_db
from app.models.user import User, UserRole, ParentStudentLink, GapAnalysis
from app.models.academic import (
    TestResult, Test, ClassStudent, Section, Class, Subject,
    TeacherAssignment, Topic, Chapter,
)
from app.models.homework import HomeworkSubmission
from app.core.dependencies import get_current_user, check_ai_token_limit
from app.services.analytics import get_student_performance
from app.services.ai import analyze_class_performance, ai_chat_json

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/student/{student_id}")
async def student_dashboard(
    student_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get comprehensive performance data for a student.
    Accessible by: the student, their parents, their teachers, admin.
    """
    # Authorization
    if current_user.role == UserRole.STUDENT and str(current_user.id) != student_id:
        raise HTTPException(status_code=403, detail="You can only view your own performance")

    if current_user.role == UserRole.PARENT:
        result = await db.execute(
            select(ParentStudentLink).where(
                ParentStudentLink.parent_id == current_user.id,
                ParentStudentLink.student_id == student_id,
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Not authorized to view this student")

    performance = await get_student_performance(db, student_id)

    # Get student info
    result = await db.execute(select(User).where(User.id == student_id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Get enrolled class info
    result = await db.execute(
        select(ClassStudent, Section, Class)
        .join(Section, ClassStudent.section_id == Section.id)
        .join(Class, Section.class_id == Class.id)
        .where(ClassStudent.student_id == student_id)
    )
    enrollments = [
        {"class_name": c.name, "section_name": s.name}
        for _, s, c in result.all()
    ]

    return {
        "student": {
            "id": str(student.id),
            "name": student.full_name,
            "email": student.email,
            "admission_number": student.admission_number,
        },
        "enrollments": enrollments,
        **performance,
    }


@router.get("/class/{section_id}")
async def class_insights(
    section_id: str,
    subject_id: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Class-level learning insights.
    Shows aggregate scores, struggling topics, and student rankings.
    Uses SQL aggregation for per-student averages.
    """
    if current_user.role not in (UserRole.TEACHER, UserRole.ADMIN, UserRole.SCHOOL_ADMIN):
        raise HTTPException(status_code=403, detail="Only teachers and admins can view class insights")

    # Count students in this section (1 query)
    student_count_result = await db.execute(
        select(func.count()).select_from(ClassStudent).where(ClassStudent.section_id == section_id)
    )
    total_students = student_count_result.scalar() or 0

    # Get section/class info (1 query)
    result = await db.execute(
        select(Section, Class)
        .join(Class, Section.class_id == Class.id)
        .where(Section.id == section_id)
    )
    row = result.one_or_none()
    section_info = {"section_name": row[0].name, "class_name": row[1].name} if row else {}

    # Per-student averages via SQL aggregation (1 query)
    student_avg_q = (
        select(
            User.full_name,
            func.avg(TestResult.score),
            func.count(TestResult.id),
        )
        .join(TestResult, TestResult.student_id == User.id)
        .join(Test, TestResult.test_id == Test.id)
        .where(Test.section_id == section_id)
    )
    if subject_id:
        student_avg_q = student_avg_q.join(Topic, Test.topic_id == Topic.id).where(Topic.subject_id == subject_id)
    student_avg_q = student_avg_q.group_by(User.id, User.full_name).order_by(func.avg(TestResult.score).asc())
    student_avg_result = await db.execute(student_avg_q)
    ranked_students = [
        {"name": name, "average": round(float(avg or 0), 1), "tests_taken": count}
        for name, avg, count in student_avg_result.all()
    ]

    # Class average and total tests (1 query)
    class_agg_q = (
        select(
            func.avg(TestResult.score),
            func.count(func.distinct(TestResult.test_id)),
        )
        .join(Test, TestResult.test_id == Test.id)
        .where(Test.section_id == section_id)
    )
    if subject_id:
        class_agg_q = class_agg_q.join(Topic, Test.topic_id == Topic.id).where(Topic.subject_id == subject_id)
    class_agg_result = await db.execute(class_agg_q)
    agg_row = class_agg_result.one()
    class_average = round(float(agg_row[0] or 0), 1)
    total_tests = agg_row[1] or 0

    return {
        **section_info,
        "total_students": total_students,
        "class_average": class_average,
        "total_tests": total_tests,
        "students_ranked": ranked_students,
        "common_weak_areas": [],  # Now loaded lazily per chapter via /weak-chapters + /weak-areas/{chapter_id}
    }


@router.get("/class/{section_id}/ai-insights")
async def class_ai_insights(
    section_id: str,
    current_user: User = Depends(check_ai_token_limit),
    db: AsyncSession = Depends(get_db),
):
    """AI-powered class-level insights with recommendations."""
    if current_user.role not in (UserRole.TEACHER, UserRole.ADMIN, UserRole.SCHOOL_ADMIN):
        raise HTTPException(status_code=403, detail="Only teachers and admins")

    # Get class data
    insights = await class_insights(section_id, None, current_user, db)

    # Prepare data for AI analysis
    data_summary = f"""
Class: {insights.get('class_name', 'Unknown')} Section: {insights.get('section_name', 'Unknown')}
Total Students: {insights['total_students']}
Class Average: {insights['class_average']}%

Students (by performance):
{chr(10).join(f"- {s['name']}: {s['average']}% ({s['tests_taken']} tests)" for s in insights['students_ranked'][:20])}
"""

    ai_result = await analyze_class_performance(db, current_user.id, data_summary)

    return {
        **insights,
        "ai_analysis": ai_result,
    }


# ── Chapter-Based Weak Areas (Lazy-Loaded + AI-Grouped) ──────
import time as _time
import json as _json

# In-memory cache: {(section_id, chapter_id): {"data": [...], "ts": float}}
_weak_areas_cache: dict = {}
_CACHE_TTL = 3600  # 1 hour


@router.get("/class/{section_id}/weak-chapters")
async def weak_chapters(
    section_id: str,
    subject_id: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List chapters with gap counts for a section — for the accordion UI."""
    if current_user.role not in (UserRole.TEACHER, UserRole.ADMIN, UserRole.SCHOOL_ADMIN):
        raise HTTPException(403, "Teachers and admins only")

    # Get all student IDs in this section
    students_result = await db.execute(
        select(ClassStudent.student_id).where(ClassStudent.section_id == section_id)
    )
    student_ids = [r[0] for r in students_result.all()]
    if not student_ids:
        return []

    # Count gaps per chapter for all students in section
    gap_q = (
        select(
            GapAnalysis.chapter_id,
            Chapter.name,
            func.count(GapAnalysis.id),
        )
        .outerjoin(Chapter, GapAnalysis.chapter_id == Chapter.id)
        .where(
            GapAnalysis.student_id.in_(student_ids),
            GapAnalysis.status == "open",
        )
    )
    if subject_id:
        gap_q = gap_q.where(GapAnalysis.subject_id == subject_id)
    gap_q = gap_q.group_by(GapAnalysis.chapter_id, Chapter.name).order_by(func.count(GapAnalysis.id).desc())

    result = await db.execute(gap_q)
    chapters = []
    for chapter_id, chapter_name, count in result.all():
        chapters.append({
            "chapter_id": str(chapter_id) if chapter_id else None,
            "chapter_name": chapter_name or "Uncategorized",
            "gap_count": count,
        })
    return chapters


@router.get("/class/{section_id}/weak-areas/{chapter_id}")
async def weak_areas_by_chapter(
    section_id: str,
    chapter_id: str,
    subject_id: str = None,
    current_user: User = Depends(check_ai_token_limit),
    db: AsyncSession = Depends(get_db),
):
    """AI-grouped weak areas for a specific chapter. Cached 1 hour."""
    if current_user.role not in (UserRole.TEACHER, UserRole.ADMIN, UserRole.SCHOOL_ADMIN):
        raise HTTPException(403, "Teachers and admins only")

    # Check cache
    cache_key = (section_id, chapter_id, subject_id or "")
    cached = _weak_areas_cache.get(cache_key)
    if cached and (_time.time() - cached["ts"]) < _CACHE_TTL:
        return cached["data"]

    # Get student IDs in section
    students_result = await db.execute(
        select(ClassStudent.student_id).where(ClassStudent.section_id == section_id)
    )
    student_ids = [r[0] for r in students_result.all()]
    if not student_ids:
        return []

    # Fetch all gaps for this chapter
    where_clauses = [
        GapAnalysis.student_id.in_(student_ids),
        GapAnalysis.status == "open",
    ]
    if chapter_id == "null":
        where_clauses.append(GapAnalysis.chapter_id.is_(None))
    else:
        where_clauses.append(GapAnalysis.chapter_id == chapter_id)
    if subject_id:
        where_clauses.append(GapAnalysis.subject_id == subject_id)

    result = await db.execute(
        select(GapAnalysis.concept, GapAnalysis.description, User.full_name)
        .join(User, GapAnalysis.student_id == User.id)
        .where(*where_clauses)
        .order_by(GapAnalysis.created_at.desc())
        .limit(300)
    )
    rows = result.all()
    if not rows:
        _weak_areas_cache[cache_key] = {"data": [], "ts": _time.time()}
        return []

    # Build context for AI grouping
    gaps_text = "\n".join(
        f"- Student: {name} | Gap: {concept} | Detail: {desc or 'N/A'}"
        for concept, desc, name in rows
    )

    system_prompt = """You are an educational data analyst.
You will receive a list of individual student learning gaps for a specific chapter.
Group semantically similar gaps together into themes.
For each group, list the distinct student names who are struggling with that theme.

Return ONLY valid JSON — an array of objects:
[
  {
    "theme": "Short theme title (e.g. 'Confusion between mass and weight')",
    "description": "Brief explanation of what students are struggling with",
    "student_count": 4,
    "students": ["Student Name 1", "Student Name 2"]
  }
]
Sort by student_count descending. Maximum 15 groups."""

    try:
        grouped = await ai_chat_json(
            db, current_user.id, system_prompt, gaps_text, max_tokens=2048
        )
        if isinstance(grouped, list):
            result_data = grouped
        elif isinstance(grouped, dict) and "error" not in grouped:
            # AI might wrap in a key
            result_data = grouped.get("groups", grouped.get("themes", [grouped]))
        else:
            # Fallback: simple frequency count
            result_data = _fallback_grouping(rows)
    except Exception:
        result_data = _fallback_grouping(rows)

    # Cache result
    _weak_areas_cache[cache_key] = {"data": result_data, "ts": _time.time()}
    return result_data


def _fallback_grouping(rows):
    """Simple frequency count when AI grouping fails."""
    concept_students = {}
    for concept, desc, name in rows:
        concept_students.setdefault(concept, set()).add(name)
    return [
        {
            "theme": concept,
            "description": "",
            "student_count": len(students),
            "students": list(students)[:10],
        }
        for concept, students in sorted(concept_students.items(), key=lambda x: len(x[1]), reverse=True)
    ][:15]


@router.get("/my-children")
async def parent_children_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Parent sees overview of all linked children."""
    if current_user.role != UserRole.PARENT:
        raise HTTPException(status_code=403, detail="Only parents")

    result = await db.execute(
        select(ParentStudentLink, User)
        .join(User, ParentStudentLink.student_id == User.id)
        .where(ParentStudentLink.parent_id == current_user.id)
    )

    children = []
    for link, student in result.all():
        perf = await get_student_performance(db, student.id)
        children.append({
            "student_id": str(student.id),
            "name": student.full_name,
            "email": student.email,
            **perf,
        })

    return children


@router.get("/leaderboard")
async def get_leaderboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """School-wide leaderboard — top 10 students (all for admin).
    Ranked by attendance, average test score, and average homework score.
    Uses Redis cache (5 min TTL) + 3 bulk SQL queries as fallback."""
    import json
    from datetime import datetime, timedelta
    from app.models.academic import Attendance
    from app.core.redis import get_redis

    top_n = 100 if current_user.role == UserRole.ADMIN else 10
    cache_key = "leaderboard:v1"

    # Try Redis cache first
    r = get_redis()
    if r:
        try:
            cached = await r.get(cache_key)
            if cached:
                full_data = json.loads(cached)
                return {
                    "by_attendance": full_data["by_attendance"][:top_n],
                    "by_test_score": full_data["by_test_score"][:top_n],
                    "by_homework_score": full_data["by_homework_score"][:top_n],
                }
        except Exception:
            pass  # Redis error — fall through to SQL

    # Get all students with their class info (1 query)
    result = await db.execute(
        select(User, ClassStudent, Section, Class)
        .join(ClassStudent, ClassStudent.student_id == User.id)
        .join(Section, ClassStudent.section_id == Section.id)
        .join(Class, Section.class_id == Class.id)
        .where(User.role == UserRole.STUDENT, User.is_approved == True)
    )
    students_data = result.all()
    if not students_data:
        return {"by_attendance": [], "by_test_score": [], "by_homework_score": []}

    # Build student info map
    student_info = {}
    for user_obj, cs, sec, cls in students_data:
        sid = str(user_obj.id)
        student_info[sid] = {
            "name": user_obj.full_name,
            "admission_number": user_obj.admission_number or "—",
            "class_name": f"{cls.name} - {sec.name}",
        }

    thirty_days_ago = (datetime.utcnow() - timedelta(days=30)).date()

    # Bulk attendance query — 1 query for ALL students
    att_result = await db.execute(
        select(
            Attendance.student_id,
            func.count(Attendance.id).filter(Attendance.present == True),
            func.count(Attendance.id),
        )
        .where(Attendance.date >= thirty_days_ago)
        .group_by(Attendance.student_id)
    )
    att_map = {}
    for sid, present_count, total_count in att_result.all():
        att_map[str(sid)] = round((present_count / total_count * 100), 1) if total_count > 0 else 0

    # Bulk test score query — 1 query for ALL students
    test_result = await db.execute(
        select(
            TestResult.student_id,
            func.avg(TestResult.score),
        ).group_by(TestResult.student_id)
    )
    test_map = {str(sid): round(float(avg or 0), 1) for sid, avg in test_result.all()}

    # Bulk homework score query — 1 query for ALL students
    hw_result = await db.execute(
        select(
            HomeworkSubmission.student_id,
            func.avg(HomeworkSubmission.score),
        ).group_by(HomeworkSubmission.student_id)
    )
    hw_map = {str(sid): round(float(avg or 0), 1) for sid, avg in hw_result.all()}

    # Merge into leaderboard
    leaderboard = []
    for sid, info in student_info.items():
        leaderboard.append({
            **info,
            "attendance_rate": att_map.get(sid, 0),
            "avg_test_score": test_map.get(sid, 0),
            "avg_homework_score": hw_map.get(sid, 0),
        })

    # Sort each category — cache full top 100 so both admin & non-admin benefit
    by_attendance = sorted(leaderboard, key=lambda x: x["attendance_rate"], reverse=True)[:100]
    by_test = sorted(leaderboard, key=lambda x: x["avg_test_score"], reverse=True)[:100]
    by_homework = sorted(leaderboard, key=lambda x: x["avg_homework_score"], reverse=True)[:100]

    full_data = {
        "by_attendance": by_attendance,
        "by_test_score": by_test,
        "by_homework_score": by_homework,
    }

    # Cache in Redis for 5 minutes
    if r:
        try:
            await r.set(cache_key, json.dumps(full_data), ex=300)
        except Exception:
            pass  # Redis write error — non-fatal

    return {
        "by_attendance": by_attendance[:top_n],
        "by_test_score": by_test[:top_n],
        "by_homework_score": by_homework[:top_n],
    }


# ── Two-Level Lazy-Load Endpoints for Parent Ward Details ─────


@router.get("/student/{student_id}/tests-summary")
async def student_tests_summary(
    student_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lightweight test list: title, score, date — NO answers.
    Split into taken and pending."""
    from app.models.academic import ClassStudent as CS2

    # Auth: parent must be linked
    if current_user.role == UserRole.PARENT:
        link = await db.execute(
            select(ParentStudentLink).where(
                ParentStudentLink.parent_id == current_user.id,
                ParentStudentLink.student_id == student_id,
            )
        )
        if not link.scalar_one_or_none():
            raise HTTPException(403, "Not your child")

    # Find student's sections
    sec_result = await db.execute(
        select(ClassStudent.section_id).where(ClassStudent.student_id == student_id)
    )
    section_ids = [r[0] for r in sec_result.all()]

    # All tests for those sections
    tests_result = await db.execute(
        select(Test).where(Test.section_id.in_(section_ids)).order_by(Test.created_at.desc())
    )
    all_tests = tests_result.scalars().all()

    # Student's results keyed by test_id
    results_result = await db.execute(
        select(TestResult).where(TestResult.student_id == student_id)
    )
    results_map = {str(tr.test_id): tr for tr in results_result.scalars().all()}

    now = datetime.utcnow()
    taken = []
    pending = []
    missed = []
    for t in all_tests:
        tr = results_map.get(str(t.id))
        if tr:
            taken.append({
                "test_id": str(t.id),
                "result_id": str(tr.id),
                "title": t.title,
                "score": tr.score,
                "taken_at": tr.taken_at.isoformat() if tr.taken_at else None,
            })
        elif t.due_date and t.due_date < now:
            missed.append({
                "test_id": str(t.id),
                "title": t.title,
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "num_questions": t.num_questions,
            })
        else:
            pending.append({
                "test_id": str(t.id),
                "title": t.title,
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "num_questions": t.num_questions,
            })

    return {"taken": taken, "pending": pending, "missed": missed}


@router.get("/student/{student_id}/test-detail/{result_id}")
async def student_test_detail(
    student_id: str,
    result_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Full detail for ONE test result: answers, feedback, topic analysis."""
    if current_user.role == UserRole.PARENT:
        link = await db.execute(
            select(ParentStudentLink).where(
                ParentStudentLink.parent_id == current_user.id,
                ParentStudentLink.student_id == student_id,
            )
        )
        if not link.scalar_one_or_none():
            raise HTTPException(403, "Not your child")

    result = await db.execute(
        select(TestResult, Test)
        .join(Test, TestResult.test_id == Test.id)
        .where(TestResult.id == result_id, TestResult.student_id == student_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(404, "Test result not found")
    tr, t = row
    return {
        "test_title": t.title,
        "score": tr.score,
        "mode": tr.mode or "text",
        "taken_at": tr.taken_at.isoformat() if tr.taken_at else None,
        "answers": tr.answers,
        "topic_analysis": tr.topic_analysis,
    }


@router.get("/student/{student_id}/homework-summary")
async def student_homework_summary(
    student_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lightweight homework list: title, score, date — NO extracted text or feedback.
    Split into submitted and pending."""
    from app.models.homework import Homework as HW2

    if current_user.role == UserRole.PARENT:
        link = await db.execute(
            select(ParentStudentLink).where(
                ParentStudentLink.parent_id == current_user.id,
                ParentStudentLink.student_id == student_id,
            )
        )
        if not link.scalar_one_or_none():
            raise HTTPException(403, "Not your child")

    sec_result = await db.execute(
        select(ClassStudent.section_id).where(ClassStudent.student_id == student_id)
    )
    section_ids = [r[0] for r in sec_result.all()]

    # All homework for sections
    from app.models.homework import Homework as HW
    hw_result = await db.execute(
        select(HW).where(HW.section_id.in_(section_ids)).order_by(HW.created_at.desc())
    )
    all_hw = hw_result.scalars().all()

    # Student's submissions keyed by homework_id
    sub_result = await db.execute(
        select(HomeworkSubmission).where(HomeworkSubmission.student_id == student_id)
    )
    subs_map = {str(s.homework_id): s for s in sub_result.scalars().all()}

    now = datetime.utcnow()
    submitted = []
    pending = []
    missed = []
    for hw in all_hw:
        sub = subs_map.get(str(hw.id))
        if sub:
            submitted.append({
                "homework_id": str(hw.id),
                "submission_id": str(sub.id),
                "title": hw.title,
                "score": sub.score,
                "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
            })
        elif hw.due_date and hw.due_date < now:
            missed.append({
                "homework_id": str(hw.id),
                "title": hw.title,
                "description": hw.description,
                "due_date": hw.due_date.isoformat() if hw.due_date else None,
            })
        else:
            pending.append({
                "homework_id": str(hw.id),
                "title": hw.title,
                "description": hw.description,
                "due_date": hw.due_date.isoformat() if hw.due_date else None,
            })

    return {"submitted": submitted, "pending": pending, "missed": missed}


@router.get("/student/{student_id}/homework-detail/{submission_id}")
async def student_homework_detail(
    student_id: str,
    submission_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Full detail for ONE homework submission: extracted text, AI feedback, typed answer."""
    from app.models.homework import Homework as HW

    if current_user.role == UserRole.PARENT:
        link = await db.execute(
            select(ParentStudentLink).where(
                ParentStudentLink.parent_id == current_user.id,
                ParentStudentLink.student_id == student_id,
            )
        )
        if not link.scalar_one_or_none():
            raise HTTPException(403, "Not your child")

    result = await db.execute(
        select(HomeworkSubmission, HW)
        .join(HW, HomeworkSubmission.homework_id == HW.id)
        .where(HomeworkSubmission.id == submission_id, HomeworkSubmission.student_id == student_id)
    )
    row = result.first()
    if not row:
        raise HTTPException(404, "Submission not found")
    sub, hw = row
    return {
        "title": hw.title,
        "description": hw.description,
        "score": sub.score,
        "ai_feedback": sub.ai_feedback,
        "extracted_text": sub.extracted_text,
        "text_content": sub.text_content,
        "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
    }


# ── Gap Analysis Endpoints ───────────────────────────────────


@router.get("/student/{student_id}/gap-chapters")
async def student_gap_chapters(
    student_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get chapter summary for a student's open gaps (chapter_id, name, count)."""
    if current_user.role == UserRole.PARENT:
        link = await db.execute(
            select(ParentStudentLink).where(
                ParentStudentLink.parent_id == current_user.id,
                ParentStudentLink.student_id == student_id,
            )
        )
        if not link.scalar_one_or_none():
            raise HTTPException(403, "Not your child")
    elif current_user.role == UserRole.STUDENT:
        if str(current_user.id) != student_id:
            raise HTTPException(403, "Can only view own gaps")

    result = await db.execute(
        select(
            GapAnalysis.chapter_id,
            func.count(GapAnalysis.id),
        )
        .where(GapAnalysis.student_id == student_id, GapAnalysis.status == "open")
        .group_by(GapAnalysis.chapter_id)
    )
    chapters = []
    for chapter_id, count in result.all():
        ch_name = "Uncategorized"
        if chapter_id:
            ch = await db.get(Chapter, chapter_id)
            if ch:
                cls = await db.get(Class, ch.class_id) if ch.class_id else None
                ch_name = f"{ch.name} [{cls.name}]" if cls else ch.name
        chapters.append({"chapter_id": str(chapter_id) if chapter_id else None, "name": ch_name, "count": count})
    return chapters


@router.get("/student/{student_id}/gaps")
async def student_gaps(
    student_id: str,
    chapter_id: str = None,
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a student's open gap analysis cards (paginated, optionally filtered by chapter)."""
    if current_user.role == UserRole.PARENT:
        link = await db.execute(
            select(ParentStudentLink).where(
                ParentStudentLink.parent_id == current_user.id,
                ParentStudentLink.student_id == student_id,
            )
        )
        if not link.scalar_one_or_none():
            raise HTTPException(403, "Not your child")
    elif current_user.role == UserRole.STUDENT:
        if str(current_user.id) != student_id:
            raise HTTPException(403, "Can only view own gaps")

    where_clauses = [GapAnalysis.student_id == student_id, GapAnalysis.status == "open"]
    if chapter_id:
        if chapter_id == "null":
            where_clauses.append(GapAnalysis.chapter_id.is_(None))
        else:
            where_clauses.append(GapAnalysis.chapter_id == chapter_id)

    base = select(GapAnalysis).where(*where_clauses)

    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total = count_result.scalar() or 0

    result = await db.execute(
        base.order_by(GapAnalysis.created_at.desc()).limit(limit).offset(offset)
    )
    gaps = result.scalars().all()

    out = []
    for g in gaps:
        subj_name = ""
        topic_name = ""
        chapter_name = ""
        if g.subject_id:
            subj = await db.get(Subject, g.subject_id)
            subj_name = subj.name if subj else ""
        if g.topic_id:
            topic = await db.get(Topic, g.topic_id)
            topic_name = topic.title if topic else ""
        if g.chapter_id:
            chapter = await db.get(Chapter, g.chapter_id)
            chapter_name = chapter.name if chapter else ""

        out.append({
            "id": str(g.id),
            "concept": g.concept,
            "description": g.description,
            "suggestion": g.suggestion,
            "severity": g.severity,
            "source": g.source,
            "subject": subj_name,
            "topic": topic_name,
            "chapter": chapter_name,
            "created_at": g.created_at.isoformat() if g.created_at else None,
        })
    return {"items": out, "total": total, "limit": limit, "offset": offset}


@router.get("/class-gap-summary/{section_id}")
async def class_gap_summary(
    section_id: str,
    subject_id: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get student list with gap counts for a section. Teacher/admin only."""
    if current_user.role not in (UserRole.TEACHER, UserRole.ADMIN, UserRole.SCHOOL_ADMIN):
        raise HTTPException(403, "Teachers and admins only")

    students_result = await db.execute(
        select(ClassStudent.student_id).where(ClassStudent.section_id == section_id)
    )
    student_ids = [r[0] for r in students_result.all()]
    if not student_ids:
        return []

    where_clauses = [GapAnalysis.student_id.in_(student_ids), GapAnalysis.status == "open"]
    if subject_id:
        where_clauses.append(GapAnalysis.subject_id == subject_id)

    result = await db.execute(
        select(GapAnalysis.student_id, User.full_name, func.count(GapAnalysis.id))
        .join(User, GapAnalysis.student_id == User.id)
        .where(*where_clauses)
        .group_by(GapAnalysis.student_id, User.full_name)
        .order_by(User.full_name)
    )
    return [
        {"student_id": str(sid), "student_name": name, "gap_count": count}
        for sid, name, count in result.all()
    ]


@router.get("/class-gap-chapters/{section_id}/{student_id}")
async def class_gap_chapters(
    section_id: str,
    student_id: str,
    subject_id: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get chapter list with gap counts for a specific student in a section."""
    if current_user.role not in (UserRole.TEACHER, UserRole.ADMIN, UserRole.SCHOOL_ADMIN):
        raise HTTPException(403, "Teachers and admins only")

    where_clauses = [GapAnalysis.student_id == student_id, GapAnalysis.status == "open"]
    if subject_id:
        where_clauses.append(GapAnalysis.subject_id == subject_id)

    result = await db.execute(
        select(GapAnalysis.chapter_id, func.count(GapAnalysis.id))
        .where(*where_clauses)
        .group_by(GapAnalysis.chapter_id)
    )
    chapters = []
    for chapter_id, count in result.all():
        ch_name = "Uncategorized"
        if chapter_id:
            ch = await db.get(Chapter, chapter_id)
            if ch:
                cls = await db.get(Class, ch.class_id) if ch.class_id else None
                ch_name = f"{ch.name} [{cls.name}]" if cls else ch.name
        chapters.append({"chapter_id": str(chapter_id) if chapter_id else None, "name": ch_name, "count": count})
    return chapters


@router.get("/class-gaps/{section_id}")
async def class_gaps(
    section_id: str,
    subject_id: str = None,
    student_id: str = None,
    chapter_id: str = None,
    limit: int = 20,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get open gaps for students in a section (paginated). Supports student_id and chapter_id filters."""
    if current_user.role not in (UserRole.TEACHER, UserRole.ADMIN, UserRole.SCHOOL_ADMIN):
        raise HTTPException(403, "Teachers and admins only")

    if student_id:
        target_ids = [student_id]
    else:
        students_result = await db.execute(
            select(ClassStudent.student_id).where(ClassStudent.section_id == section_id)
        )
        target_ids = [r[0] for r in students_result.all()]
    if not target_ids:
        return {"items": [], "total": 0, "limit": limit, "offset": offset}

    base_where = [
        GapAnalysis.student_id.in_(target_ids),
        GapAnalysis.status == "open",
    ]
    if subject_id:
        base_where.append(GapAnalysis.subject_id == subject_id)
    if chapter_id:
        if chapter_id == "null":
            base_where.append(GapAnalysis.chapter_id.is_(None))
        else:
            base_where.append(GapAnalysis.chapter_id == chapter_id)

    base = (
        select(GapAnalysis, User)
        .join(User, GapAnalysis.student_id == User.id)
        .where(*base_where)
    )

    count_q = select(func.count()).select_from(
        select(GapAnalysis.id)
        .where(*base_where)
        .subquery()
    )
    count_result = await db.execute(count_q)
    total = count_result.scalar() or 0

    result = await db.execute(
        base.order_by(User.full_name, GapAnalysis.created_at.desc()).limit(limit).offset(offset)
    )
    rows = result.all()

    out = []
    for g, u in rows:
        subj_name = ""
        chapter_name = ""
        if g.subject_id:
            subj = await db.get(Subject, g.subject_id)
            subj_name = subj.name if subj else ""
        if g.chapter_id:
            chapter = await db.get(Chapter, g.chapter_id)
            chapter_name = chapter.name if chapter else ""
        out.append({
            "id": str(g.id),
            "student_name": u.full_name,
            "student_id": str(u.id),
            "concept": g.concept,
            "description": g.description,
            "suggestion": g.suggestion,
            "severity": g.severity,
            "source": g.source,
            "subject": subj_name,
            "chapter": chapter_name,
            "created_at": g.created_at.isoformat() if g.created_at else None,
        })
    return {"items": out, "total": total, "limit": limit, "offset": offset}


@router.put("/gaps/{gap_id}/resolve")
async def resolve_gap(
    gap_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a gap as resolved."""
    gap = await db.get(GapAnalysis, gap_id)
    if not gap:
        raise HTTPException(404, "Gap not found")

    # Auth: student can resolve own, teacher/admin can resolve any
    if current_user.role == UserRole.STUDENT and str(gap.student_id) != str(current_user.id):
        raise HTTPException(403, "Not your gap")
    if current_user.role == UserRole.PARENT:
        raise HTTPException(403, "Only students and teachers can resolve gaps")

    gap.status = "resolved"
    await db.flush()
    return {"message": "Gap resolved"}


@router.delete("/class/{section_id}/resolve-chapter/{chapter_id}")
async def resolve_chapter_gaps(
    section_id: str,
    chapter_id: str,
    subject_id: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Bulk-resolve all open gaps for students in a section+chapter."""
    if current_user.role not in (UserRole.TEACHER, UserRole.ADMIN, UserRole.SCHOOL_ADMIN):
        raise HTTPException(403, "Teachers and admins only")

    # Get student IDs in section
    students_result = await db.execute(
        select(ClassStudent.student_id).where(ClassStudent.section_id == section_id)
    )
    student_ids = [r[0] for r in students_result.all()]
    if not student_ids:
        return {"message": "No students in section", "deleted": 0}

    where = [
        GapAnalysis.student_id.in_(student_ids),
        GapAnalysis.status == "open",
    ]
    if chapter_id == "null":
        where.append(GapAnalysis.chapter_id.is_(None))
    else:
        where.append(GapAnalysis.chapter_id == chapter_id)
    if subject_id:
        where.append(GapAnalysis.subject_id == subject_id)

    from sqlalchemy import delete as sql_delete
    result = await db.execute(sql_delete(GapAnalysis).where(*where))
    await db.flush()

    # Clear cache for this section
    keys_to_del = [k for k in _weak_areas_cache if k[0] == section_id]
    for k in keys_to_del:
        del _weak_areas_cache[k]

    return {"message": "Chapter gaps resolved", "deleted": result.rowcount}


# ── Learn with AI (Personalized Learning) ────────────────────
@router.post("/learn")
async def learn_with_ai(
    req: dict,
    current_user: User = Depends(check_ai_token_limit),
    db: AsyncSession = Depends(get_db),
):
    """Personalized learning: student asks about a topic, AI teaches at their level."""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(403, "Only students can use Learn with AI")

    topic_query = (req.get("query") or "").strip()
    if not topic_query:
        raise HTTPException(400, "Please enter a topic to learn about")

    # Get student's class info
    class_result = await db.execute(
        select(Section, Class)
        .join(Class, Section.class_id == Class.id)
        .join(ClassStudent, ClassStudent.section_id == Section.id)
        .where(ClassStudent.student_id == current_user.id)
    )
    class_row = class_result.first()
    class_info = f"{class_row[1].name} - {class_row[0].name}" if class_row else "Unknown class"

    # Get student's open gaps (up to 20)
    gaps_result = await db.execute(
        select(GapAnalysis.concept, GapAnalysis.description)
        .where(GapAnalysis.student_id == current_user.id, GapAnalysis.status == "open")
        .order_by(GapAnalysis.created_at.desc())
        .limit(20)
    )
    gaps = gaps_result.all()
    gaps_text = "\n".join(f"- {c}: {d or 'N/A'}" for c, d in gaps) if gaps else "No known gaps."

    system_prompt = f"""You are a friendly, expert tutor teaching a student in {class_info}.
The student has the following known learning gaps:
{gaps_text}

INSTRUCTIONS:
- Explain the topic at the appropriate class level
- If the topic relates to any of the student's gaps, address those gaps directly
- Use simple language, examples, and analogies appropriate for the student's level
- Structure your response with clear headings and bullet points
- Include a quick practice question at the end
- Keep the response focused and not too long (aim for 300-500 words)"""

    from app.services.ai import ai_chat
    response = await ai_chat(db, current_user.id, system_prompt, f"Teach me about: {topic_query}", max_tokens=2048)

    return {"response": response, "class_info": class_info, "gaps_count": len(gaps)}
