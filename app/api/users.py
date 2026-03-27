"""
User API — profile management, student/teacher onboarding, parent linking, join requests.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.database import get_db
from app.models.user import (
    User, UserRole, JoinRequest, JoinRequestStatus,
    ParentStudentLink, OTPPurpose,
)
from app.models.academic import ClassStudent, Section, Class, TeacherAssignment
from app.schemas.user import (
    StudentProfileUpdate, TeacherProfileUpdate,
    ParentLinkRequest, ParentLinkVerify, UserResponse,
    JoinRequestCreate, JoinRequestResponse, JoinRequestAction,
)
from app.core.dependencies import get_current_user, require_verified_user
from app.services.email import send_otp_email, verify_otp

router = APIRouter(prefix="/api/users", tags=["Users"])


# ── Teacher Assignments (for dropdowns) ───────────────────────

@router.get("/my-assignments")
async def get_my_assignments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get teacher's assigned sections and subjects for use in dropdowns."""
    if current_user.role == UserRole.ADMIN:
        # Admin gets all sections and subjects
        from app.models.academic import Subject
        sec_result = await db.execute(
            select(Section, Class)
            .join(Class, Section.class_id == Class.id)
            .order_by(Class.name, Section.name)
        )
        sections = [
            {"id": str(s.id), "label": f"{c.name} - {s.name}", "class_id": str(c.id)}
            for s, c in sec_result.all()
        ]
        subj_result = await db.execute(select(Subject).order_by(Subject.name))
        subjects = [
            {"id": str(s.id), "name": s.name}
            for s in subj_result.scalars().all()
        ]
        return {"sections": sections, "subjects": subjects}

    if current_user.role != UserRole.TEACHER:
        return {"sections": [], "subjects": []}

    from app.models.academic import Subject
    result = await db.execute(
        select(TeacherAssignment, Section, Class, Subject)
        .join(Section, TeacherAssignment.section_id == Section.id)
        .join(Class, Section.class_id == Class.id)
        .join(Subject, TeacherAssignment.subject_id == Subject.id)
        .where(TeacherAssignment.teacher_id == current_user.id)
    )

    sections_map = {}
    subjects_map = {}
    class_map = {}
    for ta, sec, cls, subj in result.all():
        sections_map[str(sec.id)] = f"{cls.name} - {sec.name}"
        class_map[str(sec.id)] = str(cls.id)
        subjects_map[str(subj.id)] = subj.name

    return {
        "sections": [{"id": k, "label": v, "class_id": class_map.get(k, "")} for k, v in sections_map.items()],
        "subjects": [{"id": k, "name": v} for k, v in subjects_map.items()],
    }



# ── Profile ───────────────────────────────────────────────────

@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """Get current user's profile."""
    return _user_to_response(current_user)


@router.put("/me/student-profile")
async def update_student_profile(
    req: StudentProfileUpdate,
    current_user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
):
    """Step 2 for students: fill admission number and guardian info."""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students can update student profile")

    current_user.admission_number = req.admission_number
    current_user.guardian_name = req.guardian_name
    current_user.guardian_phone = req.guardian_phone
    await db.flush()

    return {"message": "Profile updated", "user": _user_to_response(current_user)}


@router.put("/me/teacher-profile")
async def update_teacher_profile(
    req: TeacherProfileUpdate,
    current_user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
):
    """Step 2 for teachers: fill employee ID and department, then notify admin."""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(status_code=403, detail="Only teachers can update teacher profile")

    current_user.employee_id = req.employee_id
    current_user.department = req.department
    await db.flush()

    # Create a join request for admin approval (no section needed for teacher initial approval)
    existing = await db.execute(
        select(JoinRequest).where(
            JoinRequest.user_id == current_user.id,
            JoinRequest.section_id == None,
            JoinRequest.status == JoinRequestStatus.PENDING,
        )
    )
    if not existing.scalar_one_or_none():
        db.add(JoinRequest(
            user_id=current_user.id,
            section_id=None,
            status=JoinRequestStatus.PENDING,
        ))
        await db.flush()

    return {"message": "Profile updated. Awaiting admin approval."}


# ── Join Requests (Student → Class/Section) ──────────────────

@router.get("/sections/available")
async def list_available_sections(
    current_user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
):
    """List all classes/sections available for joining."""
    result = await db.execute(
        select(Section, Class)
        .join(Class, Section.class_id == Class.id)
        .order_by(Class.name, Section.name)
    )
    sections = []
    for section, cls in result.all():
        sections.append({
            "section_id": str(section.id),
            "section_name": section.name,
            "class_id": str(cls.id),
            "class_name": cls.name,
            "display": f"{cls.name} - {section.name}",
        })
    return sections


@router.post("/join-request")
async def create_join_request(
    req: JoinRequestCreate,
    current_user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
):
    """Student requests to join a class/section."""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students can request to join a class")

    # Check if student already has a pending/approved request for this section
    existing = await db.execute(
        select(JoinRequest).where(
            JoinRequest.user_id == current_user.id,
            JoinRequest.section_id == req.section_id,
            JoinRequest.status.in_([JoinRequestStatus.PENDING, JoinRequestStatus.APPROVED]),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="You already have a request for this section")

    # Check if student is already enrolled
    existing_enrollment = await db.execute(
        select(ClassStudent).where(
            ClassStudent.student_id == current_user.id,
            ClassStudent.section_id == req.section_id,
        )
    )
    if existing_enrollment.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="You are already enrolled in this section")

    join_req = JoinRequest(
        user_id=current_user.id,
        section_id=req.section_id,
        status=JoinRequestStatus.PENDING,
    )
    db.add(join_req)
    await db.flush()

    return {"message": "Join request sent. Awaiting class teacher approval.", "request_id": str(join_req.id)}


@router.get("/join-requests/pending")
async def get_pending_join_requests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get pending join requests.
    - Admin: sees teacher join requests (section_id is NULL)
    - Class teacher: sees student join requests for their sections
    """
    requests = []

    if current_user.role == UserRole.ADMIN:
        # Teacher approval requests (section_id is NULL)
        result = await db.execute(
            select(JoinRequest, User)
            .join(User, JoinRequest.user_id == User.id)
            .where(
                JoinRequest.status == JoinRequestStatus.PENDING,
                JoinRequest.section_id == None,
            )
        )
        for jr, user in result.all():
            requests.append({
                "id": str(jr.id),
                "user_id": str(user.id),
                "user_name": user.full_name,
                "user_email": user.email,
                "user_role": user.role.value,
                "section_id": None,
                "section_name": None,
                "class_name": None,
                "status": jr.status.value,
                "created_at": jr.created_at.isoformat() if jr.created_at else None,
            })

    if current_user.role in (UserRole.TEACHER, UserRole.ADMIN):
        # Get sections where current user is class teacher
        teacher_sections = []
        if current_user.role == UserRole.TEACHER:
            result = await db.execute(
                select(TeacherAssignment.section_id).where(
                    TeacherAssignment.teacher_id == current_user.id,
                    TeacherAssignment.is_class_teacher == True,
                )
            )
            teacher_sections = [r[0] for r in result.all()]
        elif current_user.role == UserRole.ADMIN:
            # Admin sees all student join requests
            result = await db.execute(select(Section.id))
            teacher_sections = [r[0] for r in result.all()]

        if teacher_sections:
            result = await db.execute(
                select(JoinRequest, User, Section, Class)
                .join(User, JoinRequest.user_id == User.id)
                .join(Section, JoinRequest.section_id == Section.id)
                .join(Class, Section.class_id == Class.id)
                .where(
                    JoinRequest.status == JoinRequestStatus.PENDING,
                    JoinRequest.section_id.in_(teacher_sections),
                )
            )
            for jr, user, section, cls in result.all():
                requests.append({
                    "id": str(jr.id),
                    "user_id": str(user.id),
                    "user_name": user.full_name,
                    "user_email": user.email,
                    "user_role": user.role.value,
                    "section_id": str(section.id),
                    "section_name": section.name,
                    "class_name": cls.name,
                    "status": jr.status.value,
                    "created_at": jr.created_at.isoformat() if jr.created_at else None,
                })

    return requests


@router.put("/join-requests/{request_id}")
async def action_join_request(
    request_id: str,
    action: JoinRequestAction,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve or reject a join request."""
    result = await db.execute(select(JoinRequest).where(JoinRequest.id == request_id))
    join_req = result.scalar_one_or_none()
    if not join_req:
        raise HTTPException(status_code=404, detail="Join request not found")

    if join_req.status != JoinRequestStatus.PENDING:
        raise HTTPException(status_code=400, detail="Request already processed")

    # Determine permission
    if join_req.section_id is None:
        # Teacher approval — only admin
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Only admin can approve teacher requests")
    else:
        # Student approval — class teacher or admin
        if current_user.role == UserRole.TEACHER:
            ta_result = await db.execute(
                select(TeacherAssignment).where(
                    TeacherAssignment.teacher_id == current_user.id,
                    TeacherAssignment.section_id == join_req.section_id,
                    TeacherAssignment.is_class_teacher == True,
                )
            )
            if not ta_result.scalar_one_or_none():
                raise HTTPException(status_code=403, detail="You are not the class teacher for this section")
        elif current_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=403, detail="Not authorized")

    new_status = action.status.lower()
    if new_status not in ("approved", "rejected"):
        raise HTTPException(status_code=400, detail="Status must be 'approved' or 'rejected'")

    join_req.status = JoinRequestStatus(new_status)
    join_req.reviewed_by = current_user.id

    if new_status == "approved":
        # Get the user being approved
        result = await db.execute(select(User).where(User.id == join_req.user_id))
        user = result.scalar_one()

        if user.role == UserRole.TEACHER:
            # Mark teacher as approved
            user.is_approved = True

        elif user.role == UserRole.STUDENT and join_req.section_id:
            # Enroll student in section
            user.is_approved = True
            db.add(ClassStudent(
                student_id=user.id,
                section_id=join_req.section_id,
            ))

    await db.flush()
    return {"message": f"Request {new_status}"}


# ── Parent Linking ───────────────────────────────────────────

@router.post("/parent/link-request")
async def parent_link_request(
    req: ParentLinkRequest,
    current_user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
):
    """Parent enters student's email → OTP sent to student's email."""
    if current_user.role != UserRole.PARENT:
        raise HTTPException(status_code=403, detail="Only parents can link to students")

    # Find student
    result = await db.execute(
        select(User).where(User.email == req.student_email, User.role == UserRole.STUDENT)
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found with this email")

    if not student.is_email_verified:
        raise HTTPException(status_code=400, detail="Student has not verified their email yet")

    # Check if student has joined a class
    result = await db.execute(
        select(ClassStudent).where(ClassStudent.student_id == student.id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Student must join a class before a parent can link. Ask the student to join a class first."
        )

    # Check if already linked
    result = await db.execute(
        select(ParentStudentLink).where(
            ParentStudentLink.parent_id == current_user.id,
            ParentStudentLink.student_id == student.id,
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Already linked to this student")

    # Send OTP to student's email (10 min expiry)
    await send_otp_email(db, student.email, OTPPurpose.PARENT_LINK, expiry_minutes=10)

    return {"message": f"OTP sent to student's email ({student.email}). Ask your ward to share the code."}


@router.post("/parent/link-verify")
async def parent_link_verify(
    req: ParentLinkVerify,
    current_user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
):
    """Parent enters OTP code to complete the link."""
    if current_user.role != UserRole.PARENT:
        raise HTTPException(status_code=403, detail="Only parents can link to students")

    # Verify OTP
    valid = await verify_otp(db, req.student_email, req.code, OTPPurpose.PARENT_LINK)
    if not valid:
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    # Find student
    result = await db.execute(
        select(User).where(User.email == req.student_email, User.role == UserRole.STUDENT)
    )
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Create link
    db.add(ParentStudentLink(parent_id=current_user.id, student_id=student.id))
    current_user.is_approved = True  # Parent is now approved
    await db.flush()

    return {"message": f"Successfully linked to {student.full_name}"}


@router.get("/parent/has-links")
async def parent_has_links(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check if a parent has any linked students. Used by frontend redirect guard."""
    if current_user.role != UserRole.PARENT:
        return {"has_links": True}  # Non-parents always pass

    result = await db.execute(
        select(ParentStudentLink.id).where(
            ParentStudentLink.parent_id == current_user.id
        ).limit(1)
    )
    has_links = result.scalar_one_or_none() is not None
    return {"has_links": has_links}


# ── Helpers ──────────────────────────────────────────────────

def _user_to_response(user: User) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "phone": user.phone,
        "role": user.role.value,
        "is_email_verified": user.is_email_verified,
        "is_approved": user.is_approved,
        "admission_number": user.admission_number,
        "guardian_name": user.guardian_name,
        "guardian_phone": user.guardian_phone,
        "employee_id": user.employee_id,
        "department": user.department,
        "relationship_type": user.relationship_type,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }
