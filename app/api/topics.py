"""
Topics API — teacher uploads class notes, OCR extracts text, stores as topics.
Also provides Chapter CRUD with searchable autocomplete.
"""

import os
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User, UserRole
from app.models.academic import Topic, Chapter, TeacherAssignment, Section, Subject, Class
from app.core.dependencies import get_current_user, check_ai_token_limit
from app.services.ocr import extract_text_from_image
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/api/topics", tags=["Topics"])


# ── Chapter Endpoints ────────────────────────────────────────

@router.get("/chapters")
async def search_chapters(
    q: str = "",
    class_id: str = None,
    subject_id: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Search chapters with autocomplete. Filtered by teacher + class + subject."""
    if current_user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Only teachers can search chapters")

    query = select(Chapter, Class, Subject).join(
        Class, Chapter.class_id == Class.id
    ).outerjoin(
        Subject, Chapter.subject_id == Subject.id
    )

    # Teacher sees only their own chapters
    if current_user.role == UserRole.TEACHER:
        query = query.where(Chapter.teacher_id == current_user.id)

    if class_id:
        query = query.where(Chapter.class_id == class_id)
    if subject_id:
        query = query.where(Chapter.subject_id == subject_id)
    if q:
        query = query.where(Chapter.name.ilike(f"%{q}%"))

    query = query.order_by(Chapter.name).limit(20)
    result = await db.execute(query)

    return [
        {
            "id": str(ch.id),
            "name": ch.name,
            "class_id": str(ch.class_id),
            "class_name": cls.name if cls else "",
            "subject_id": str(ch.subject_id) if ch.subject_id else None,
            "subject_name": subj.name if subj else "",
        }
        for ch, cls, subj in result.all()
    ]


@router.post("/chapters", status_code=201)
async def create_chapter(
    req: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new chapter. Requires name, class_id. subject_id is optional."""
    if current_user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Only teachers can create chapters")

    name = (req.get("name") or "").strip()
    class_id = req.get("class_id")
    subject_id = req.get("subject_id") or None

    if not name:
        raise HTTPException(status_code=400, detail="Chapter name is required")
    if not class_id:
        raise HTTPException(status_code=400, detail="Class is required")

    # Check for duplicate
    existing_q = select(Chapter).where(
        Chapter.teacher_id == current_user.id,
        Chapter.class_id == class_id,
        Chapter.name == name,
    )
    if subject_id:
        existing_q = existing_q.where(Chapter.subject_id == subject_id)
    else:
        existing_q = existing_q.where(Chapter.subject_id.is_(None))

    existing = await db.execute(existing_q)
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Chapter already exists")

    chapter = Chapter(
        name=name,
        teacher_id=current_user.id,
        class_id=class_id,
        subject_id=subject_id,
    )
    db.add(chapter)
    await db.flush()

    return {"id": str(chapter.id), "name": chapter.name, "message": "Chapter created"}


# ── Topic Endpoints ──────────────────────────────────────────

@router.post("/upload", status_code=201)
async def upload_topic(
    title: str = Form(...),
    section_id: str = Form(...),
    subject_id: str = Form(...),
    chapter_id: str = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(check_ai_token_limit),
    db: AsyncSession = Depends(get_db),
):
    """
    Teacher uploads a photo of class notes.
    AI extracts text via OCR → stored as a topic.
    """
    if current_user.role not in (UserRole.TEACHER, UserRole.ADMIN):
        raise HTTPException(status_code=403, detail="Only teachers can upload topics")

    # Verify teacher is assigned to this section/subject (or admin)
    if current_user.role == UserRole.TEACHER:
        result = await db.execute(
            select(TeacherAssignment).where(
                TeacherAssignment.teacher_id == current_user.id,
                TeacherAssignment.section_id == section_id,
                TeacherAssignment.subject_id == subject_id,
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=403, detail="You are not assigned to this section/subject")

    # Validate file type
    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/jpg",
                     "application/pdf", "application/msword",
                     "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Only images, PDF, and DOC files are allowed")

    # Save file
    upload_dir = Path(settings.UPLOAD_DIR) / "topics"
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4()}{Path(file.filename).suffix}"
    file_path = upload_dir / filename

    content = await file.read()
    if len(content) > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"File too large. Max {settings.MAX_UPLOAD_SIZE_MB}MB")

    with open(file_path, "wb") as f:
        f.write(content)

    # OCR — extract text from image
    try:
        extracted_text = await extract_text_from_image(db, current_user.id, str(file_path))
    except Exception as e:
        extracted_text = f"OCR extraction failed: {str(e)}"

    # Create topic
    topic = Topic(
        section_id=section_id,
        subject_id=subject_id,
        teacher_id=current_user.id,
        chapter_id=chapter_id if chapter_id else None,
        title=title,
        extracted_text=extracted_text,
        image_path=str(file_path),
    )
    db.add(topic)
    await db.flush()

    return {
        "id": str(topic.id),
        "title": topic.title,
        "extracted_text": extracted_text,
        "image_path": str(file_path),
        "message": "Topic created successfully",
    }


@router.get("/")
async def list_topics(
    section_id: str = None,
    subject_id: str = None,
    class_id: str = None,
    chapter_id: str = None,
    limit: int = 10,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List topics, paginated, optionally filtered by section, subject, class, or chapter."""
    query = (
        select(Topic, Subject, Section, Class, Chapter)
        .join(Subject, Topic.subject_id == Subject.id)
        .join(Section, Topic.section_id == Section.id)
        .join(Class, Section.class_id == Class.id)
        .outerjoin(Chapter, Topic.chapter_id == Chapter.id)
    )

    if class_id:
        query = query.where(Section.class_id == class_id)
    if section_id:
        query = query.where(Topic.section_id == section_id)
    if subject_id:
        query = query.where(Topic.subject_id == subject_id)
    if chapter_id:
        query = query.where(Topic.chapter_id == chapter_id)

    # Teachers see only their topics; students see topics for their sections
    if current_user.role == UserRole.TEACHER:
        query = query.where(Topic.teacher_id == current_user.id)

    query = query.order_by(Topic.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)

    return [
        {
            "id": str(t.id),
            "title": t.title,
            "section_id": str(t.section_id),
            "subject_id": str(t.subject_id),
            "subject_name": subj.name,
            "class_name": cls.name,
            "section_name": sec.name,
            "chapter_id": str(t.chapter_id) if t.chapter_id else None,
            "chapter_name": ch.name if ch else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        }
        for t, subj, sec, cls, ch in result.all()
    ]


@router.get("/{topic_id}")
async def get_topic(
    topic_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a single topic with its extracted text."""
    result = await db.execute(
        select(Topic, Subject, Chapter)
        .join(Subject, Topic.subject_id == Subject.id)
        .outerjoin(Chapter, Topic.chapter_id == Chapter.id)
        .where(Topic.id == topic_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Topic not found")
    t, s, ch = row
    return {
        "id": str(t.id),
        "title": t.title,
        "extracted_text": t.extracted_text,
        "section_id": str(t.section_id),
        "subject_id": str(t.subject_id),
        "subject_name": s.name,
        "chapter_id": str(t.chapter_id) if t.chapter_id else None,
        "chapter_name": ch.name if ch else None,
        "image_path": t.image_path,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }
