"""
Homework API — assign, submit, AI-check, view results.
"""

import uuid
import json
from pathlib import Path
from typing import List
import logging

logger = logging.getLogger(__name__)
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime

from app.database import get_db
from app.models.user import User, UserRole, GapAnalysis, AISettings
from app.models.homework import Homework, HomeworkSubmission
from app.models.academic import TeacherAssignment, ClassStudent, Subject, Section, Chapter
from app.schemas.homework import HomeworkCreate
from app.core.dependencies import get_current_user, check_ai_token_limit
from app.services.ocr import extract_text_from_image
from app.services.ai import check_homework, analyze_gaps, get_cached_setting
from app.services.analytics import check_and_create_alerts
from app.models.communication import Alert, AlertType
from app.models.user import ParentStudentLink
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/api/homework", tags=["Homework"])


@router.post("/", status_code=201)
async def assign_homework(
    title: str = Form(...),
    section_id: str = Form(...),
    subject_id: str = Form(...),
    due_date: str = Form(...),
    submission_type: str = Form("both"),
    description: str = Form(None),
    chapter_id: str = Form(None),
    file: UploadFile = File(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Teacher assigns homework. Can upload image for description (OCR extracts text)."""
    if current_user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Only teachers can assign homework")

    if current_user.role == UserRole.TEACHER:
        result = await db.execute(
            select(TeacherAssignment).where(
                TeacherAssignment.teacher_id == current_user.id,
                TeacherAssignment.section_id == section_id,
                TeacherAssignment.subject_id == subject_id,
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="Not assigned to this section/subject")

    try:
        parsed_due_date = datetime.fromisoformat(due_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid due_date format")

    # Reject past deadlines
    if parsed_due_date < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Deadline cannot be in the past")

    # If teacher uploads an image, extract text as description
    hw_description = description or ""
    if file and file.filename:
        upload_dir = Path(settings.UPLOAD_DIR) / "homework_desc"
        upload_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid.uuid4()}{Path(file.filename).suffix}"
        fp = upload_dir / filename
        content = await file.read()
        with open(fp, "wb") as f:
            f.write(content)
        try:
            extracted = await extract_text_from_image(db, current_user.id, str(fp))
            hw_description = extracted if extracted else hw_description
        except Exception:
            pass  # Keep original description if OCR fails

    homework = Homework(
        section_id=section_id,
        subject_id=subject_id,
        teacher_id=current_user.id,
        chapter_id=chapter_id if chapter_id else None,
        title=title,
        description=hw_description,
        due_date=parsed_due_date,
        submission_type=submission_type,
    )
    db.add(homework)
    await db.flush()

    # ── Send alerts to students and parents (bulk) ──
    try:
        enrolled = await db.execute(
            select(ClassStudent.student_id).where(ClassStudent.section_id == section_id)
        )
        student_ids = [r[0] for r in enrolled.all()]

        if student_ids:
            # Bulk: parent links (1 query)
            parent_result = await db.execute(
                select(ParentStudentLink.student_id, ParentStudentLink.parent_id)
                .where(ParentStudentLink.student_id.in_(student_ids))
            )
            student_parents = {}
            for sid, pid in parent_result.all():
                student_parents.setdefault(sid, []).append(pid)

            # Bulk: student names (1 query)
            name_result = await db.execute(
                select(User.id, User.full_name).where(User.id.in_(student_ids))
            )
            student_names = {uid: name for uid, name in name_result.all()}

            due_str = parsed_due_date.strftime('%b %d, %Y %I:%M %p')
            push_targets = []

            for student_id in student_ids:
                student_name = student_names.get(student_id, "Your child")
                # Alert the student
                db.add(Alert(
                    student_id=student_id,
                    recipient_id=student_id,
                    alert_type=AlertType.NEW_HOMEWORK,
                    message=f"📚 New homework assigned: {title}. Due: {due_str}.",
                ))
                push_targets.append((student_id, f"📚 New Homework", f"{title} — Due: {parsed_due_date.strftime('%b %d')}"))
                # Alert parents
                for parent_id in student_parents.get(student_id, []):
                    db.add(Alert(
                        student_id=student_id,
                        recipient_id=parent_id,
                        alert_type=AlertType.NEW_HOMEWORK,
                        message=f"📚 New homework for {student_name}: {title}. Due: {due_str}.",
                    ))
                    push_targets.append((parent_id, "📚 New Homework", f"{student_name}: {title}"))

            await db.flush()

            # Push notifications
            try:
                from app.api.push import send_push_to_user
                for rid, ptitle, pbody in push_targets:
                    await send_push_to_user(db, rid, ptitle, pbody, "/dashboard")
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"[HOMEWORK] Alert creation failed: {e}")

    return {"id": str(homework.id), "message": "Homework assigned"}


@router.put("/{homework_id}")
async def edit_homework(
    homework_id: str,
    req: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Edit an assigned homework. Cannot edit if deadline has already passed."""
    if current_user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Only teachers/admins can edit homework")

    result = await db.execute(select(Homework).where(Homework.id == homework_id))
    homework = result.scalar_one_or_none()
    if not homework:
        raise HTTPException(status_code=404, detail="Homework not found")

    # Only the teacher who assigned it (or admin) can edit
    if current_user.role == UserRole.TEACHER and str(homework.teacher_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="You can only edit your own homework")

    # Block editing if deadline has passed
    if homework.due_date and homework.due_date < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Cannot edit homework whose deadline has already passed")

    editable = ["title", "description", "submission_type"]
    for field in editable:
        if field in req:
            setattr(homework, field, req[field])

    if "due_date" in req:
        try:
            new_due = datetime.fromisoformat(req["due_date"])
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid due_date format")
        if new_due < datetime.utcnow():
            raise HTTPException(status_code=400, detail="New deadline cannot be in the past")
        homework.due_date = new_due

    await db.flush()
    return {"message": "Homework updated"}


@router.get("/")
async def list_homework(
    section_id: str = None,
    class_id: str = None,
    sort: str = "recent",
    subject_name: str = None,
    limit: int = 10,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List homework, paginated, with sorting/filtering.

    sort options:
      - pending_first: not-submitted first, then recent (students only)
      - not_done: only not-submitted (students only)
      - recent: by due_date desc
      - all: by created_at desc
      - subject:SubjectName: filter by subject name
    """
    from app.models.academic import Class
    from sqlalchemy import case, literal

    # Parse subject filter from sort param
    filter_subject_name = None
    if sort and sort.startswith("subject:"):
        filter_subject_name = sort[len("subject:"):]
        sort = "recent"  # default ordering for subject filter

    query = (
        select(Homework, Subject, User, Section, Class, Chapter)
        .join(Subject, Homework.subject_id == Subject.id)
        .join(User, Homework.teacher_id == User.id)
        .join(Section, Homework.section_id == Section.id)
        .join(Class, Section.class_id == Class.id)
        .outerjoin(Chapter, Homework.chapter_id == Chapter.id)
    )

    if class_id:
        query = query.where(Section.class_id == class_id)
    if section_id:
        query = query.where(Homework.section_id == section_id)
    if filter_subject_name:
        query = query.where(Subject.name == filter_subject_name)

    if current_user.role == UserRole.STUDENT:
        enrolled = await db.execute(
            select(ClassStudent.section_id).where(ClassStudent.student_id == current_user.id)
        )
        section_ids = [r[0] for r in enrolled.all()]
        if section_ids:
            query = query.where(Homework.section_id.in_(section_ids))
        else:
            return []

    if current_user.role == UserRole.TEACHER:
        query = query.where(Homework.teacher_id == current_user.id)

    now = datetime.utcnow()

    # For student pending_first / not_done, use a subquery for submission status
    if current_user.role == UserRole.STUDENT and sort in ("pending_first", "not_done"):
        sub_sq = (
            select(HomeworkSubmission.homework_id)
            .where(
                HomeworkSubmission.student_id == current_user.id,
                HomeworkSubmission.homework_id == Homework.id,
            )
            .correlate(Homework)
            .exists()
        )
        if sort == "not_done":
            query = query.where(~sub_sq)
            # Not-submitted: most recent due_date first
            query = query.order_by(Homework.due_date.desc())
        else:  # pending_first
            submitted_flag = case((sub_sq, literal(1)), else_=literal(0))
            # Not-submitted first (most recent due date), then submitted (most recently created)
            query = query.order_by(submitted_flag.asc(), Homework.due_date.desc())
    elif current_user.role == UserRole.TEACHER:
        # Teacher: active homework (due_date >= now) first sorted by most recent due_date at top,
        # then past-deadline ones
        is_active = case((Homework.due_date >= now, literal(0)), else_=literal(1))
        query = query.order_by(is_active.asc(), Homework.due_date.desc())
    else:
        query = query.order_by(Homework.due_date.desc())

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    rows = result.all()

    # Bulk-fetch submitted homework IDs for this student (1 query instead of N)
    submitted_hw_ids = set()
    if current_user.role == UserRole.STUDENT and rows:
        hw_ids = [h.id for h, *_ in rows]
        sub_result = await db.execute(
            select(HomeworkSubmission.homework_id).where(
                HomeworkSubmission.student_id == current_user.id,
                HomeworkSubmission.homework_id.in_(hw_ids),
            )
        )
        submitted_hw_ids = {r[0] for r in sub_result.all()}

    homework_list = []
    for h, s, u, sec, cls, ch in rows:
        submitted = h.id in submitted_hw_ids if current_user.role == UserRole.STUDENT else False

        homework_list.append({
            "id": str(h.id),
            "title": h.title,
            "description": h.description,
            "section_id": str(h.section_id),
            "subject_id": str(h.subject_id),
            "subject_name": s.name,
            "class_name": cls.name,
            "section_name": sec.name,
            "teacher_name": u.full_name,
            "chapter_id": str(h.chapter_id) if h.chapter_id else None,
            "chapter_name": ch.name if ch else None,
            "due_date": h.due_date.isoformat() if h.due_date else None,
            "created_at": h.created_at.isoformat() if h.created_at else None,
            "submitted": submitted,
            "is_overdue": h.due_date < datetime.utcnow() if h.due_date else False,
            "submission_type": h.submission_type or "both",
        })

    return homework_list


@router.post("/{homework_id}/submit")
async def submit_homework(
    homework_id: str,
    files: List[UploadFile] = File(None),
    text_content: str = Form(None),
    current_user: User = Depends(check_ai_token_limit),
    db: AsyncSession = Depends(get_db),
):
    """Student uploads photos (multiple pages) and/or types text. AI checks quality."""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students can submit homework")

    result = await db.execute(select(Homework).where(Homework.id == homework_id))
    homework = result.scalar_one_or_none()
    if not homework:
        raise HTTPException(status_code=404, detail="Homework not found")

    # ── Reject submission after deadline ──
    if homework.due_date and homework.due_date < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Cannot submit — homework deadline has already passed")

    sub_type = homework.submission_type or "both"
    has_files = files and any(f.filename for f in files)
    if sub_type == "photo" and not has_files:
        raise HTTPException(status_code=400, detail="This homework requires a photo submission")
    if sub_type == "text" and not text_content:
        raise HTTPException(status_code=400, detail="This homework requires a text submission")
    if not has_files and not text_content:
        raise HTTPException(status_code=400, detail="Please submit a photo or text")

    existing = await db.execute(
        select(HomeworkSubmission).where(
            HomeworkSubmission.homework_id == homework_id,
            HomeworkSubmission.student_id == current_user.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="You have already submitted this homework")

    file_paths = []
    extracted_text = ""

    # Handle multiple file uploads
    if has_files:
        upload_dir = Path(settings.UPLOAD_DIR) / "homework"
        upload_dir.mkdir(parents=True, exist_ok=True)
        for i, file in enumerate(files):
            if not file.filename:
                continue
            filename = f"{uuid.uuid4()}{Path(file.filename).suffix}"
            fp = upload_dir / filename
            content = await file.read()
            with open(fp, "wb") as f:
                f.write(content)
            file_paths.append(str(fp))
            # OCR each page
            try:
                page_text = await extract_text_from_image(db, current_user.id, str(fp))
                if page_text:
                    extracted_text += f"\n--- Page {i+1} ---\n{page_text}"
            except Exception as e:
                extracted_text += f"\n--- Page {i+1} OCR failed: {str(e)} ---"

    # Combine extracted text and typed text
    eval_text = extracted_text.strip()
    if text_content:
        if eval_text:
            eval_text += "\n\n--- Typed Answer ---\n"
        eval_text += text_content

    # AI check homework
    try:
        ai_result = await check_homework(
            db, current_user.id,
            homework_description=f"{homework.title}\n{homework.description or ''}",
            extracted_text=eval_text,
        )
        ai_feedback = ai_result.get("feedback", "No feedback available")
        score = ai_result.get("score", 0)
    except Exception as e:
        ai_feedback = f"AI evaluation failed: {str(e)}"
        score = None

    submission = HomeworkSubmission(
        homework_id=homework_id,
        student_id=current_user.id,
        image_path=json.dumps(file_paths) if file_paths else None,
        text_content=text_content,
        extracted_text=extracted_text,
        ai_feedback=ai_feedback,
        score=score,
    )
    db.add(submission)
    await db.flush()

    if score is not None and score < 40:
        await check_and_create_alerts(db, current_user.id)

    # ── Notify parents if homework score is poor ──
    if score is not None and score < 50:
        try:
            parent_result = await db.execute(
                select(ParentStudentLink.parent_id).where(ParentStudentLink.student_id == current_user.id)
            )
            parent_ids = [r[0] for r in parent_result.all()]
            push_targets = []
            for parent_id in parent_ids:
                db.add(Alert(
                    student_id=current_user.id,
                    recipient_id=parent_id,
                    alert_type=AlertType.HOMEWORK_POOR,
                    message=f"⚠️ {current_user.full_name} scored {score}% on homework: {homework.title}.",
                ))
                push_targets.append((parent_id, f"⚠️ Low Homework Score", f"{current_user.full_name} scored {score}% on {homework.title}"))
            if parent_ids:
                await db.flush()
                try:
                    from app.api.push import send_push_to_user
                    for pid, ptitle, pbody in push_targets:
                        await send_push_to_user(db, pid, ptitle, pbody, "/dashboard")
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"[HOMEWORK] Parent poor-performance alert failed: {e}")

    hw_threshold = get_cached_setting("gap_homework_threshold", 50)
    if score is not None and score < hw_threshold:
        try:
            context = f"Homework: {homework.title}\nDescription: {homework.description or ''}\nScore: {score}%\nAI Feedback: {ai_feedback}\nStudent Answer (excerpt): {(eval_text or '')[:1500]}"
            gaps = await analyze_gaps(db, current_user.id, context, "homework")
            for g in gaps:
                gap = GapAnalysis(
                    student_id=current_user.id,
                    subject_id=homework.subject_id,
                    chapter_id=homework.chapter_id,
                    concept=g.get("concept", "Unknown"),
                    description=g.get("description", ""),
                    suggestion=g.get("suggestion", ""),
                    severity=g.get("severity", "moderate"),
                    source="homework",
                    source_id=submission.id,
                )
                db.add(gap)
            await db.flush()
        except Exception as e:
            logger.warning(f"[GAP ANALYSIS] Homework gap detection failed: {e}")

    return {
        "id": str(submission.id),
        "score": score,
        "ai_feedback": ai_feedback,
        "message": "Homework submitted and evaluated",
    }


@router.get("/{homework_id}/submissions")
async def get_homework_submissions(
    homework_id: str,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get submissions summary (paginated, no details)."""
    from sqlalchemy import func as sql_func
    base = (
        select(HomeworkSubmission, User)
        .join(User, HomeworkSubmission.student_id == User.id)
        .where(HomeworkSubmission.homework_id == homework_id)
    )

    if current_user.role == UserRole.STUDENT:
        base = base.where(HomeworkSubmission.student_id == current_user.id)

    # Count
    count_q = select(sql_func.count()).select_from(
        select(HomeworkSubmission.id).where(HomeworkSubmission.homework_id == homework_id).subquery()
    )
    total = (await db.execute(count_q)).scalar() or 0

    result = await db.execute(base.order_by(HomeworkSubmission.submitted_at.desc()).limit(limit).offset(offset))

    items = [
        {
            "id": str(sub.id),
            "homework_id": str(sub.homework_id),
            "student_id": str(sub.student_id),
            "student_name": u.full_name,
            "score": sub.score,
            "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
        }
        for sub, u in result.all()
    ]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/{homework_id}/submissions/{submission_id}")
async def get_submission_detail(
    homework_id: str,
    submission_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get full detail for a single homework submission (lazy-loaded)."""
    result = await db.execute(
        select(HomeworkSubmission, User)
        .join(User, HomeworkSubmission.student_id == User.id)
        .where(HomeworkSubmission.id == submission_id, HomeworkSubmission.homework_id == homework_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Submission not found")
    sub, u = row

    if current_user.role == UserRole.STUDENT and str(sub.student_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized")

    # Parse image_path — could be JSON list or single path
    image_paths = []
    if sub.image_path:
        try:
            image_paths = json.loads(sub.image_path)
        except (json.JSONDecodeError, TypeError):
            image_paths = [sub.image_path]  # Legacy single path

    return {
        "id": str(sub.id),
        "homework_id": str(sub.homework_id),
        "student_id": str(sub.student_id),
        "student_name": u.full_name,
        "score": sub.score,
        "ai_feedback": sub.ai_feedback,
        "extracted_text": sub.extracted_text,
        "text_content": sub.text_content,
        "image_paths": image_paths,
        "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
    }


@router.get("/{homework_id}/check-duplicates")
async def check_duplicates(
    homework_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check for duplicate submissions using hash-based grouping (memory-efficient)."""
    import hashlib
    if current_user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Only teachers/admins can check duplicates")

    # Get submissions with only the fields needed for hashing (no full text in memory)
    result = await db.execute(
        select(HomeworkSubmission, User)
        .join(User, HomeworkSubmission.student_id == User.id)
        .where(HomeworkSubmission.homework_id == homework_id)
    )
    submissions = result.all()

    # Hash-based grouping: compute MD5 of combined text, group by hash
    hash_groups = {}
    for sub, user in submissions:
        combined = ""
        if sub.extracted_text:
            combined += sub.extracted_text.strip()
        if sub.text_content:
            combined += sub.text_content.strip()
        if not combined:
            continue

        text_hash = hashlib.md5(combined.lower().strip().encode()).hexdigest()
        if text_hash not in hash_groups:
            hash_groups[text_hash] = {"preview": combined[:200], "students": []}
        hash_groups[text_hash]["students"].append({
            "student_id": str(sub.student_id),
            "student_name": user.full_name,
            "score": sub.score,
            "submitted_at": sub.submitted_at.isoformat() if sub.submitted_at else None,
        })

    # Return only groups with more than 1 student (actual duplicates)
    duplicates = [
        {"text_preview": g["preview"], "count": len(g["students"]), "students": g["students"]}
        for g in hash_groups.values() if len(g["students"]) > 1
    ]

    return {
        "total_submissions": len(submissions),
        "duplicate_groups": duplicates,
        "has_duplicates": len(duplicates) > 0,
    }


@router.post("/{homework_id}/redo/{submission_id}")
async def redo_homework(
    homework_id: str,
    submission_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Teacher requests a student to redo homework. Deletes submission and notifies student + parents."""
    if current_user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Only teachers/admins can request redo")

    result = await db.execute(
        select(HomeworkSubmission, Homework)
        .join(Homework, HomeworkSubmission.homework_id == Homework.id)
        .where(HomeworkSubmission.id == submission_id, HomeworkSubmission.homework_id == homework_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Submission not found")

    submission, homework = row

    # Block redo if deadline has passed
    if homework.due_date and homework.due_date < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Cannot request redo — homework deadline has already passed")

    student_id = submission.student_id

    # Delete the submission
    await db.delete(submission)

    # Create alert for the student
    db.add(Alert(
        student_id=student_id,
        recipient_id=student_id,
        alert_type=AlertType.PERFORMANCE_DROP,
        message=f"Your teacher has asked you to redo homework: {homework.title}. Please resubmit.",
    ))

    # Notify parents
    parent_result = await db.execute(
        select(ParentStudentLink.parent_id).where(ParentStudentLink.student_id == student_id)
    )
    for (parent_id,) in parent_result.all():
        db.add(Alert(
            student_id=student_id,
            recipient_id=parent_id,
            alert_type=AlertType.PERFORMANCE_DROP,
            message=f"Your child has been asked to redo homework: {homework.title}.",
        ))

    await db.flush()
    return {"message": "Submission deleted. Student and parents have been notified to redo."}


@router.get("/{homework_id}/not-submitted")
async def get_not_submitted(
    homework_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get list of students in the section who haven't submitted this homework."""
    if current_user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Only teachers/admins can view this")

    # Get homework section
    result = await db.execute(select(Homework).where(Homework.id == homework_id))
    homework = result.scalar_one_or_none()
    if not homework:
        raise HTTPException(status_code=404, detail="Homework not found")

    # Get all students enrolled in the section
    enrolled = await db.execute(
        select(ClassStudent, User)
        .join(User, ClassStudent.student_id == User.id)
        .where(ClassStudent.section_id == homework.section_id)
        .order_by(User.full_name)
    )
    all_students = enrolled.all()

    # Get students who have submitted
    submitted = await db.execute(
        select(HomeworkSubmission.student_id).where(HomeworkSubmission.homework_id == homework_id)
    )
    submitted_ids = {str(r[0]) for r in submitted.all()}

    not_submitted = [
        {"student_id": str(cs.student_id), "student_name": u.full_name}
        for cs, u in all_students
        if str(cs.student_id) not in submitted_ids
    ]

    return {
        "total_enrolled": len(all_students),
        "total_submitted": len(submitted_ids),
        "total_not_submitted": len(not_submitted),
        "students": not_submitted,
    }


@router.post("/check-deadlines")
async def check_homework_deadlines(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check all overdue homework and send HOMEWORK_MISSING alerts to parents
    of students who haven't submitted. Uses bulk queries to avoid N+1."""
    if current_user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Only teachers/admins")

    now = datetime.utcnow()

    # 1. Get overdue homework (1 query)
    result = await db.execute(
        select(Homework).where(Homework.due_date < now).order_by(Homework.due_date.desc()).limit(50)
    )
    overdue_hws = result.scalars().all()
    if not overdue_hws:
        return {"message": "0 alerts sent to parents"}

    hw_ids = [hw.id for hw in overdue_hws]
    section_ids = list({hw.section_id for hw in overdue_hws})

    # 2. Bulk: all enrolled students per section (1 query)
    enrolled_result = await db.execute(
        select(ClassStudent.section_id, ClassStudent.student_id)
        .where(ClassStudent.section_id.in_(section_ids))
    )
    section_students = {}
    for sec_id, stu_id in enrolled_result.all():
        section_students.setdefault(sec_id, set()).add(stu_id)

    # 3. Bulk: all submitters per homework (1 query)
    submitted_result = await db.execute(
        select(HomeworkSubmission.homework_id, HomeworkSubmission.student_id)
        .where(HomeworkSubmission.homework_id.in_(hw_ids))
    )
    hw_submitted = {}
    for hid, sid in submitted_result.all():
        hw_submitted.setdefault(hid, set()).add(sid)

    # 4. Collect all missing students
    all_missing_students = set()
    hw_missing_map = {}
    for hw in overdue_hws:
        enrolled = section_students.get(hw.section_id, set())
        done = hw_submitted.get(hw.id, set())
        missing = enrolled - done
        hw_missing_map[hw.id] = missing
        all_missing_students.update(missing)

    if not all_missing_students:
        return {"message": "0 alerts sent to parents"}

    # 5. Bulk: parent links (1 query)
    parent_result = await db.execute(
        select(ParentStudentLink.student_id, ParentStudentLink.parent_id)
        .where(ParentStudentLink.student_id.in_(list(all_missing_students)))
    )
    student_parents = {}
    for sid, pid in parent_result.all():
        student_parents.setdefault(sid, []).append(pid)

    # 6. Bulk: existing alerts (1 query)
    existing_alerts = await db.execute(
        select(Alert.student_id, Alert.recipient_id, Alert.message)
        .where(
            Alert.alert_type == AlertType.HOMEWORK_MISSING,
            Alert.student_id.in_(list(all_missing_students)),
        )
    )
    existing_set = {(sid, rid, msg) for sid, rid, msg in existing_alerts.all()}

    # 7. Bulk: student names (1 query)
    name_result = await db.execute(
        select(User.id, User.full_name).where(User.id.in_(list(all_missing_students)))
    )
    student_names = {uid: name for uid, name in name_result.all()}

    # Create alerts
    alerts_sent = 0
    push_targets = []
    for hw in overdue_hws:
        missing = hw_missing_map.get(hw.id, set())
        due_str = hw.due_date.strftime('%b %d, %Y %I:%M %p') if hw.due_date else ''
        for student_id in missing:
            parents = student_parents.get(student_id, [])
            student_name = student_names.get(student_id, "Your child")
            alert_msg = f"{student_name} has not submitted homework: {hw.title} (deadline was {due_str}). [hw:{hw.id}]"
            for parent_id in parents:
                if (student_id, parent_id, alert_msg) not in existing_set:
                    db.add(Alert(
                        student_id=student_id,
                        recipient_id=parent_id,
                        alert_type=AlertType.HOMEWORK_MISSING,
                        message=alert_msg,
                    ))
                    push_targets.append((parent_id, student_name, hw.title))
                    alerts_sent += 1

    await db.flush()

    if push_targets:
        try:
            from app.api.push import send_push_to_user
            for parent_id, sname, htitle in push_targets:  # Send to all parents
                await send_push_to_user(db, parent_id, "📚 Homework Missing", f"{sname} hasn't submitted: {htitle}", "/dashboard")
        except Exception:
            pass

    return {"message": f"{alerts_sent} alerts sent to parents"}
