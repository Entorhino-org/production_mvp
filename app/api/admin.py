"""
Admin API — class/section/subject management, teacher assignment, AI token limits.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from uuid import UUID

from app.database import get_db
from app.models.user import User, UserRole, AISettings, AITokenUsage
from app.models.academic import (
    Class, Section, Subject, ClassSubject, TeacherAssignment, ClassStudent,
)
from app.schemas.academic import (
    ClassCreate, ClassResponse, SectionCreate, SectionResponse,
    SubjectCreate, SubjectResponse, ClassSubjectAssign,
    TeacherAssignmentCreate, TeacherAssignmentResponse,
)
from app.core.dependencies import require_admin, require_super_admin
from app.core.security import hash_password

router = APIRouter(prefix="/api/admin", tags=["Admin"])


# ── Classes ───────────────────────────────────────────────────

@router.post("/classes", status_code=201)
async def create_class(
    req: ClassCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new school class (e.g., '10th')."""
    existing = await db.execute(select(Class).where(Class.name == req.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Class already exists")

    cls = Class(name=req.name)
    db.add(cls)
    await db.flush()
    return {"id": str(cls.id), "name": cls.name}


@router.get("/classes")
async def list_classes(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all classes with their sections."""
    result = await db.execute(select(Class).order_by(Class.name))
    classes = []
    for cls in result.scalars().all():
        sec_result = await db.execute(
            select(Section).where(Section.class_id == cls.id).order_by(Section.name)
        )
        sections = [
            {"id": str(s.id), "name": s.name, "class_id": str(cls.id)}
            for s in sec_result.scalars().all()
        ]
        classes.append({"id": str(cls.id), "name": cls.name, "sections": sections})
    return classes


@router.delete("/classes/{class_id}")
async def delete_class(
    class_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a class and all its sections."""
    result = await db.execute(select(Class).where(Class.id == class_id))
    cls = result.scalar_one_or_none()
    if not cls:
        raise HTTPException(status_code=404, detail="Class not found")
    await db.delete(cls)
    await db.flush()
    return {"message": "Class deleted"}


# ── Sections ──────────────────────────────────────────────────

@router.post("/sections", status_code=201)
async def create_section(
    req: SectionCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a section within a class (e.g., 'A' in '10th')."""
    # Check class exists
    cls = await db.execute(select(Class).where(Class.id == req.class_id))
    if not cls.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Class not found")

    # Check duplicate
    existing = await db.execute(
        select(Section).where(Section.class_id == req.class_id, Section.name == req.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Section already exists in this class")

    section = Section(class_id=req.class_id, name=req.name)
    db.add(section)
    await db.flush()
    return {"id": str(section.id), "name": section.name, "class_id": str(section.class_id)}


@router.delete("/sections/{section_id}")
async def delete_section(
    section_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Section).where(Section.id == section_id))
    section = result.scalar_one_or_none()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    await db.delete(section)
    await db.flush()
    return {"message": "Section deleted"}


# ── Subjects ──────────────────────────────────────────────────

@router.post("/subjects", status_code=201)
async def create_subject(
    req: SubjectCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a subject (e.g., 'Mathematics')."""
    existing = await db.execute(select(Subject).where(Subject.name == req.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Subject already exists")

    subject = Subject(name=req.name)
    db.add(subject)
    await db.flush()
    return {"id": str(subject.id), "name": subject.name}


@router.get("/subjects")
async def list_subjects(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Subject).order_by(Subject.name))
    return [{"id": str(s.id), "name": s.name} for s in result.scalars().all()]


@router.delete("/subjects/{subject_id}")
async def delete_subject(
    subject_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Subject).where(Subject.id == subject_id))
    subject = result.scalar_one_or_none()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    await db.delete(subject)
    await db.flush()
    return {"message": "Subject deleted"}


# ── Assign Subject to Class ──────────────────────────────────

@router.post("/class-subjects", status_code=201)
async def assign_subject_to_class(
    req: ClassSubjectAssign,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Assign a subject to a class (applies to all sections)."""
    existing = await db.execute(
        select(ClassSubject).where(
            ClassSubject.class_id == req.class_id,
            ClassSubject.subject_id == req.subject_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Subject already assigned to this class")

    cs = ClassSubject(class_id=req.class_id, subject_id=req.subject_id)
    db.add(cs)
    await db.flush()
    return {"message": "Subject assigned to class"}


@router.get("/class-subjects/{class_id}")
async def get_class_subjects(
    class_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get all subjects assigned to a class."""
    result = await db.execute(
        select(ClassSubject, Subject)
        .join(Subject, ClassSubject.subject_id == Subject.id)
        .where(ClassSubject.class_id == class_id)
    )
    return [
        {"id": str(cs.id), "subject_id": str(s.id), "subject_name": s.name}
        for cs, s in result.all()
    ]


@router.delete("/class-subjects/{class_subject_id}")
async def remove_subject_from_class(
    class_subject_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ClassSubject).where(ClassSubject.id == class_subject_id))
    cs = result.scalar_one_or_none()
    if not cs:
        raise HTTPException(status_code=404, detail="Assignment not found")
    await db.delete(cs)
    await db.flush()
    return {"message": "Subject removed from class"}


# ── Teacher Assignments ──────────────────────────────────────

@router.post("/teacher-assignments", status_code=201)
async def assign_teacher(
    req: TeacherAssignmentCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Assign a teacher to a class/section/subject.
    Flow: admin selects class → section → subject from assigned subjects.
    """
    # Validate teacher exists and is approved
    result = await db.execute(select(User).where(User.id == req.teacher_id, User.role == UserRole.TEACHER))
    teacher = result.scalar_one_or_none()
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    if not teacher.is_approved:
        raise HTTPException(status_code=400, detail="Teacher not yet approved")

    # If marking as class teacher, check no other class teacher for this section
    if req.is_class_teacher:
        existing = await db.execute(
            select(TeacherAssignment).where(
                TeacherAssignment.section_id == req.section_id,
                TeacherAssignment.is_class_teacher == True,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="This section already has a class teacher")

    # Check duplicate
    existing = await db.execute(
        select(TeacherAssignment).where(
            TeacherAssignment.teacher_id == req.teacher_id,
            TeacherAssignment.section_id == req.section_id,
            TeacherAssignment.subject_id == req.subject_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Teacher already assigned to this section/subject")

    ta = TeacherAssignment(
        teacher_id=req.teacher_id,
        section_id=req.section_id,
        subject_id=req.subject_id,
        is_class_teacher=req.is_class_teacher,
    )
    db.add(ta)
    await db.flush()
    return {"message": "Teacher assigned", "id": str(ta.id)}


@router.get("/teacher-assignments")
async def list_teacher_assignments(
    limit: int = 100,
    offset: int = 0,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all teacher assignments (paginated)."""
    limit = min(limit, 200)
    result = await db.execute(
        select(TeacherAssignment, User, Section, Class, Subject)
        .join(User, TeacherAssignment.teacher_id == User.id)
        .join(Section, TeacherAssignment.section_id == Section.id)
        .join(Class, Section.class_id == Class.id)
        .join(Subject, TeacherAssignment.subject_id == Subject.id)
        .offset(offset).limit(limit)
    )
    return [
        {
            "id": str(ta.id),
            "teacher_id": str(u.id),
            "teacher_name": u.full_name,
            "section_id": str(s.id),
            "section_name": s.name,
            "class_name": c.name,
            "subject_id": str(sub.id),
            "subject_name": sub.name,
            "is_class_teacher": ta.is_class_teacher,
        }
        for ta, u, s, c, sub in result.all()
    ]


@router.delete("/teacher-assignments/{assignment_id}")
async def remove_teacher_assignment(
    assignment_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(TeacherAssignment).where(TeacherAssignment.id == assignment_id))
    ta = result.scalar_one_or_none()
    if not ta:
        raise HTTPException(status_code=404, detail="Assignment not found")
    await db.delete(ta)
    await db.flush()
    return {"message": "Teacher assignment removed"}


# ── AI Token Settings ────────────────────────────────────────

@router.get("/ai-settings")
async def get_ai_settings(
    admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AISettings).limit(1))
    settings = result.scalar_one_or_none()
    defaults = {
        "daily_student_limit": 5000, "daily_teacher_limit": 15000,
        "ai_model": "google/gemini-2.0-flash-001",
        "ocr_model": "google/gemini-2.0-flash-001",
        "evaluation_model": "google/gemini-2.0-flash-001",
        "otp_sender_email": "", "otp_sender_password": "",
        "smtp_host": "smtp.gmail.com", "smtp_port": 587,
        "school_name": "My School",
        "resend_api_key": "", "resend_from_email": "",
        "gap_test_threshold": 60, "gap_homework_threshold": 50,
        "openrouter_api_key": "",
        "gemini_api_key": "",
        "sarvam_api_key": "",
        "vad_silence_ms": 2000,
        "vad_sensitivity": "END_SENSITIVITY_HIGH",
        "vad_proactivity": False,
    }
    if not settings:
        return defaults
    return {k: getattr(settings, k, v) for k, v in defaults.items()}


@router.put("/ai-settings")
async def update_ai_settings(
    req: dict,
    admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AISettings).limit(1))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = AISettings()
        db.add(settings)

    editable = ["daily_student_limit", "daily_teacher_limit",
                "ai_model", "ocr_model", "evaluation_model",
                "otp_sender_email", "otp_sender_password", "smtp_host", "smtp_port",
                "school_name", "resend_api_key", "resend_from_email",
                "gap_test_threshold", "gap_homework_threshold",
                "openrouter_api_key", "gemini_api_key",
                "sarvam_api_key",
                "vad_silence_ms", "vad_sensitivity", "vad_proactivity"]
    for field in editable:
        if field in req:
            setattr(settings, field, req[field])

    await db.flush()

    # Reload in-memory cache so changes take effect immediately
    from app.services.ai import reload_cached_settings
    await reload_cached_settings(db)

    return {"message": "Settings updated"}


# ── API Keys (multi-key round-robin) ─────────────────────────

@router.get("/api-keys")
async def list_api_keys(
    admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.models.user import ApiKey
    result = await db.execute(select(ApiKey).order_by(ApiKey.created_at.desc()))
    keys = result.scalars().all()
    return [
        {
            "id": str(k.id),
            "provider": k.provider,
            "label": k.label or "",
            "key_preview": f"{k.api_key[:8]}...{k.api_key[-4:]}" if len(k.api_key) > 12 else "****",
            "error_count": k.error_count or 0,
            "last_error": k.last_error or "",
            "created_at": k.created_at.isoformat() if k.created_at else "",
        }
        for k in keys
    ]


@router.post("/api-keys")
async def add_api_key(
    req: dict,
    admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    import httpx
    from app.models.user import ApiKey
    provider = req.get("provider", "").strip()
    api_key = req.get("api_key", "").strip()
    label = req.get("label", "").strip()

    if provider not in ("openrouter", "openai", "sarvam", "gemini"):
        raise HTTPException(400, "Provider must be 'openrouter', 'openai', 'sarvam', or 'gemini'")
    if not api_key:
        raise HTTPException(400, "API key is required")

    # ── Validate key with a test request ──
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            if provider == "openai":
                resp = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
            elif provider == "sarvam":
                # Validate by POSTing to Sarvam TTS endpoint with minimal payload
                # Valid key → 422/400 (missing required fields), Invalid key → 401/403
                resp = await client.post(
                    "https://api.sarvam.ai/text-to-speech",
                    headers={"api-subscription-key": api_key, "Content-Type": "application/json"},
                    json={"inputs": ["test"], "target_language_code": "en-IN"},
                )
                # 200 = worked, 422/400 = key valid but bad params, both mean valid key
                if resp.status_code in (200, 422, 400):
                    resp.status_code = 200  # Key is valid
            elif provider == "gemini":
                # Validate Gemini key by listing models
                resp = await client.get(
                    "https://generativelanguage.googleapis.com/v1beta/models",
                    params={"key": api_key},
                )
            else:
                resp = await client.get(
                    "https://openrouter.ai/api/v1/auth/key",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
            if resp.status_code == 401:
                raise HTTPException(400, "Invalid API key — authentication failed")
            if resp.status_code >= 400:
                raise HTTPException(400, f"API key validation failed: HTTP {resp.status_code}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(400, f"Could not validate key: {str(e)[:200]}")

    new_key = ApiKey(provider=provider, api_key=api_key, label=label)
    db.add(new_key)
    await db.flush()

    from app.services.ai import reload_cached_settings
    await reload_cached_settings(db)

    return {"message": "API key validated and added", "id": str(new_key.id)}


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: str,
    admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.models.user import ApiKey
    result = await db.execute(select(ApiKey).where(ApiKey.id == key_id))
    key = result.scalar_one_or_none()
    if not key:
        raise HTTPException(404, "API key not found")

    await db.delete(key)
    await db.flush()

    from app.services.ai import reload_cached_settings
    await reload_cached_settings(db)

    return {"message": "API key deleted"}


# ── User Management ──────────────────────────────────────────

@router.get("/users")
async def list_users(
    role: str = None,
    search: str = None,
    limit: int = 100,
    offset: int = 0,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List users, optionally filter by role and search by name/admission number."""
    if limit == 0:
        limit = 5000  # "All" option
    else:
        limit = min(max(limit, 1), 500)
    query = select(User).order_by(User.created_at.desc())
    if role:
        try:
            role_enum = UserRole(role)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid role: {role}")
        query = query.where(User.role == role_enum)
    if search and search.strip():
        s = f"%{search.strip()}%"
        from sqlalchemy import or_
        query = query.where(
            or_(
                User.full_name.ilike(s),
                User.email.ilike(s),
                User.admission_number.ilike(s),
                User.phone.ilike(s),
            )
        )
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    return [
        {
            "id": str(u.id),
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role.value,
            "is_email_verified": u.is_email_verified,
            "is_approved": u.is_approved,
            "phone": u.phone,
            "admission_number": u.admission_number,
            "employee_id": u.employee_id,
            "department": u.department,
            "guardian_name": u.guardian_name,
            "guardian_phone": u.guardian_phone,
        }
        for u in result.scalars().all()
    ]


@router.get("/student/{student_id}/details")
async def get_student_details(
    student_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed analytics for a student (admin view)."""
    from app.services.analytics import get_student_performance
    result = await db.execute(select(User).where(User.id == student_id))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    perf = await get_student_performance(db, student.id)

    # Get class/section info
    enrollment = await db.execute(
        select(ClassStudent, Section, Class)
        .join(Section, ClassStudent.section_id == Section.id)
        .join(Class, Section.class_id == Class.id)
        .where(ClassStudent.student_id == student_id)
    )
    class_info = []
    for cs, sec, cls in enrollment.all():
        class_info.append({"class": cls.name, "section": sec.name})

    return {
        "id": str(student.id),
        "full_name": student.full_name,
        "email": student.email,
        "phone": student.phone,
        "admission_number": student.admission_number,
        "guardian_name": student.guardian_name,
        "guardian_phone": student.guardian_phone,
        "classes": class_info,
        **perf,
    }


@router.get("/approved-teachers")
async def list_approved_teachers(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List approved teachers for assignment dropdown."""
    result = await db.execute(
        select(User).where(User.role == UserRole.TEACHER, User.is_approved == True)
        .order_by(User.full_name)
    )
    return [
        {"id": str(u.id), "full_name": u.full_name, "email": u.email, "department": u.department}
        for u in result.scalars().all()
    ]


# ── User CRUD ────────────────────────────────────────────────

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a user account."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == UserRole.ADMIN:
        raise HTTPException(status_code=400, detail="Cannot delete admin accounts")
    await db.delete(user)
    await db.flush()
    return {"message": f"User {user.full_name} deleted"}


@router.put("/users/{user_id}")
async def edit_user(
    user_id: str,
    req: dict,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Edit user details (name, email, phone, admission_number, employee_id, etc)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    editable = ["full_name", "email", "phone", "admission_number",
                 "employee_id", "department", "guardian_name", "guardian_phone"]
    for field in editable:
        if field in req and req[field] is not None:
            setattr(user, field, req[field])

    # Admin can also approve/unapprove
    if "is_approved" in req:
        user.is_approved = req["is_approved"]

    await db.flush()
    return {"message": f"User {user.full_name} updated"}


# ── Parent-Student Links ─────────────────────────────────────

@router.get("/parent-links")
async def get_parent_links(
    limit: int = 100,
    offset: int = 0,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all parent-student links (paginated, single JOIN query)."""
    from app.models.user import ParentStudentLink
    from sqlalchemy.orm import aliased
    from sqlalchemy import func as sql_func
    Parent = aliased(User, name="parent_user")
    Student = aliased(User, name="student_user")

    # Count
    count_result = await db.execute(select(sql_func.count()).select_from(ParentStudentLink))
    total = count_result.scalar() or 0

    result = await db.execute(
        select(ParentStudentLink, Parent, Student)
        .join(Parent, ParentStudentLink.parent_id == Parent.id)
        .join(Student, ParentStudentLink.student_id == Student.id)
        .limit(limit).offset(offset)
    )
    items = [
        {
            "id": str(link.id),
            "parent_id": str(link.parent_id),
            "parent_name": parent.full_name,
            "parent_email": parent.email,
            "parent_phone": parent.phone,
            "relationship": parent.relationship_type,
            "student_id": str(link.student_id),
            "student_name": student.full_name,
            "student_email": student.email,
            "student_admission": student.admission_number,
        }
        for link, parent, student in result.all()
    ]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


# ── All Feedback (Admin View) ────────────────────────────────

@router.get("/all-feedback")
async def get_all_feedback(
    limit: int = 100,
    offset: int = 0,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin view: all feedback (paginated, single JOIN query)."""
    from app.models.communication import Feedback
    from sqlalchemy.orm import aliased
    from sqlalchemy import func as sql_func
    Teacher = aliased(User, name="teacher_user")
    Student = aliased(User, name="student_user")

    count_result = await db.execute(select(sql_func.count()).select_from(Feedback))
    total = count_result.scalar() or 0

    result = await db.execute(
        select(Feedback, Teacher, Student)
        .join(Teacher, Feedback.teacher_id == Teacher.id)
        .join(Student, Feedback.student_id == Student.id, isouter=True)
        .order_by(Feedback.created_at.desc())
        .limit(limit).offset(offset)
    )
    items = [
        {
            "id": str(f.id),
            "teacher_name": teacher.full_name if teacher else "Unknown",
            "student_name": student.full_name if student else "Anonymous",
            "content": f.content,
            "rating": f.rating,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        }
        for f, teacher, student in result.all()
    ]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


# ── Server Logs (Super Admin only) ───────────────────────────

@router.get("/server-logs")
async def get_server_logs(
    level: str = "error",
    max_lines: int = 200,
    admin: User = Depends(require_super_admin),
):
    """Read recent error/warning logs from uvicorn.log (tail-based, never loads full file)."""
    import os
    log_file = "uvicorn.log"
    if not os.path.exists(log_file):
        return {"lines": [], "total": 0}

    # Read last ~50KB of the file (tail approach)
    max_bytes = 50 * 1024
    file_size = os.path.getsize(log_file)
    read_start = max(0, file_size - max_bytes)

    with open(log_file, "r", errors="replace") as f:
        f.seek(read_start)
        if read_start > 0:
            f.readline()  # Skip partial first line
        raw_lines = f.readlines()

    # Filter by level
    level_upper = level.upper()
    if level_upper == "ERROR":
        keywords = ["ERROR", "Traceback", "Exception", "raise "]
    elif level_upper == "WARNING":
        keywords = ["WARNING", "ERROR", "Traceback", "Exception"]
    else:
        keywords = []  # all

    filtered = []
    in_traceback = False
    for line in raw_lines:
        stripped = line.rstrip()
        if not stripped:
            in_traceback = False
            continue
        if any(kw in stripped for kw in ["Traceback", "ERROR", "WARNING", "Exception"]):
            in_traceback = True
        if keywords:
            if in_traceback or any(kw in stripped for kw in keywords):
                filtered.append(stripped)
        else:
            filtered.append(stripped)
        if stripped.startswith("INFO:") or stripped.startswith("DEBUG:"):
            in_traceback = False

    # Return last N lines
    result_lines = filtered[-max_lines:] if len(filtered) > max_lines else filtered
    return {"lines": result_lines, "total": len(filtered)}


# ── All Class-Subject Assignments ────────────────────────────

@router.get("/class-subjects-all")
async def get_all_class_subjects(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get all class-subject assignments grouped by class."""
    result = await db.execute(
        select(ClassSubject, Class, Subject)
        .join(Class, ClassSubject.class_id == Class.id)
        .join(Subject, ClassSubject.subject_id == Subject.id)
        .order_by(Class.name, Subject.name)
    )
    return [
        {
            "id": str(cs.id),
            "class_id": str(c.id),
            "class_name": c.name,
            "subject_id": str(s.id),
            "subject_name": s.name,
        }
        for cs, c, s in result.all()
    ]


# ── Create School Admin ──────────────────────────────────────

@router.post("/create-school-admin", status_code=201)
async def create_school_admin(
    req: dict,
    admin: User = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a school admin account (super admin only)."""
    email = req.get("email", "").strip()
    password = req.get("password", "")
    full_name = req.get("full_name", "").strip()
    phone = req.get("phone", "").strip() or None

    if not email or not password or not full_name:
        raise HTTPException(status_code=400, detail="Email, password, and name are required")

    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    # Check if email already exists
    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name=full_name,
        phone=phone,
        role=UserRole.SCHOOL_ADMIN,
        is_email_verified=True,
        is_approved=True,
    )
    db.add(user)
    await db.flush()
    return {"id": str(user.id), "message": f"School admin '{full_name}' created successfully"}
