"""
Gap Analysis v2.0 API — composite Gap Index (GI) computation, prerequisite
DAG management, signal ingestion, and remedial plan access.

Endpoints
---------
POST /api/gaps/compute                  Compute GI for one (student, topic)
POST /api/gaps/compute-bulk             Compute GI for all topics of a student
GET  /api/gaps/student/{student_id}     List GI records for a student
GET  /api/gaps/student/{student_id}/{topic_id}  Single GI record
POST /api/gaps/prerequisites            Add a prerequisite edge
DELETE /api/gaps/prerequisites/{id}     Remove a prerequisite edge
GET  /api/gaps/prerequisites/{topic_id} List prerequisites of a topic
POST /api/gaps/signals/quiz             Ingest quiz responses
POST /api/gaps/signals/assignment       Ingest assignment submission
POST /api/gaps/signals/comprehension    Ingest comprehension score
POST /api/gaps/signals/engagement       Ingest engagement event
POST /api/gaps/remedial/generate/{student_id}  Trigger remedial plan generation
"""

from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, check_ai_token_limit
from app.database import get_db
from app.models.academic import Topic
from app.models.gaps import (
    AssignmentSubmission,
    ComprehensionScore,
    EngagementEvent,
    QuizResponse,
    StudentGap,
    TopicPrerequisite,
)
from app.models.user import User, UserRole, ParentStudentLink
from app.schemas.gaps import (
    AssignmentSubmissionCreate,
    BulkComputeGIRequest,
    ComprehensionScoreCreate,
    ComputeGIRequest,
    EngagementEventCreate,
    GapSignalsResponse,
    QuizResponseCreate,
    StudentGapResponse,
    TopicPrerequisiteCreate,
    TopicPrerequisiteResponse,
)
from app.services.gap_analysis import (
    GI_THRESHOLD,
    compute_and_persist,
    compute_bulk_and_propagate,
    propagate_risks,
)
from app.services.remedial import (
    generate_remedial_plan,
    schedule_remedial_for_high_gi_gaps,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/gaps", tags=["Gap Analysis v2"])


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

async def _assert_can_access_student(
    current_user: User,
    student_id: str,
    db: AsyncSession,
):
    """Raise 403 if current_user cannot view student_id's data."""
    if current_user.role in (UserRole.ADMIN, UserRole.SCHOOL_ADMIN, UserRole.TEACHER):
        return
    if current_user.role == UserRole.STUDENT and str(current_user.id) == student_id:
        return
    if current_user.role == UserRole.PARENT:
        link = await db.execute(
            select(ParentStudentLink).where(
                ParentStudentLink.parent_id == current_user.id,
                ParentStudentLink.student_id == student_id,
            )
        )
        if link.scalar_one_or_none():
            return
    raise HTTPException(status_code=403, detail="Not authorised to access this student's data")


def _gap_to_response(gap: StudentGap, topic_title: Optional[str] = None) -> StudentGapResponse:
    return StudentGapResponse(
        id=str(gap.id),
        student_id=str(gap.student_id),
        topic_id=str(gap.topic_id),
        topic_title=topic_title,
        gap_index=gap.gap_index,
        gap_score=gap.gap_score,
        signals=GapSignalsResponse(
            quiz_score=gap.quiz_score,
            assignment_score=gap.assignment_score,
            comprehension_index=gap.comprehension_index,
            engagement_depth_ratio=gap.engagement_depth_ratio,
            peer_benchmark_normalized=gap.peer_benchmark_normalized,
            source_flags=gap.source_flags,
        ),
        computed_at=gap.computed_at.isoformat() if gap.computed_at else None,
        signal_window_days=gap.signal_window_days,
        is_propagated_risk=gap.is_propagated_risk,
        propagated_from_topic_id=(
            str(gap.propagated_from_topic_id) if gap.propagated_from_topic_id else None
        ),
        propagation_depth=gap.propagation_depth,
        propagation_decay_factor=gap.propagation_decay_factor,
        remedial_plan=gap.remedial_plan,
        status=gap.status,
        created_at=gap.created_at.isoformat() if gap.created_at else None,
    )


# ─────────────────────────────────────────────────────────────
# GI Computation
# ─────────────────────────────────────────────────────────────

@router.post("/compute", response_model=StudentGapResponse)
async def compute_gi(
    body: ComputeGIRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Compute (or recompute) the composite Gap Index for a single
    (student, topic) pair.

    If GI > threshold after computation, a background task is scheduled to
    generate the LLM remedial plan.

    Access: teacher, admin, school_admin, or the student themselves.
    """
    await _assert_can_access_student(current_user, body.student_id, db)

    # Validate topic exists
    topic = await db.get(Topic, body.topic_id)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    try:
        gap = await compute_and_persist(
            db,
            UUID(body.student_id),
            UUID(body.topic_id),
            signal_window_days=body.signal_window_days,
        )
    except Exception as exc:
        logger.exception("[API] compute_gi failed: %s", exc)
        raise HTTPException(status_code=500, detail="GI computation failed")

    # Run propagation
    try:
        await propagate_risks(db, UUID(body.student_id))
    except Exception as exc:
        logger.warning("[API] propagate_risks failed: %s", exc)

    await db.commit()

    # Background: generate remedial plan if GI is high
    if gap.gap_index > GI_THRESHOLD:
        background_tasks.add_task(
            _background_remedial,
            body.student_id,
            body.topic_id,
        )

    return _gap_to_response(gap, topic.title)


async def _background_remedial(student_id: str, topic_id: str):
    """Background task — generate remedial plan after GI computation."""
    from app.database import async_session

    async with async_session() as db:
        result = await db.execute(
            select(StudentGap).where(
                and_(
                    StudentGap.student_id == UUID(student_id),
                    StudentGap.topic_id == UUID(topic_id),
                    StudentGap.is_propagated_risk == False,
                )
            )
        )
        gap = result.scalar_one_or_none()
        if gap and gap.remedial_plan is None:
            try:
                await generate_remedial_plan(db, gap)
                await db.commit()
            except Exception as exc:
                logger.error("[BG] Remedial plan generation failed: %s", exc)
                await db.rollback()


@router.post("/compute-bulk")
async def compute_gi_bulk(
    body: BulkComputeGIRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Compute GI for all topics accessible to the student (based on their
    sections), then run prerequisite propagation.

    Returns a summary of computed / propagated gap counts.
    Access: teacher, admin, school_admin.
    """
    if current_user.role not in (UserRole.TEACHER, UserRole.ADMIN, UserRole.SCHOOL_ADMIN):
        raise HTTPException(status_code=403, detail="Only teachers and admins can trigger bulk computation")

    # Gather topics associated with the student's sections
    from app.models.academic import ClassStudent, Section
    sections_result = await db.execute(
        select(ClassStudent.section_id).where(ClassStudent.student_id == body.student_id)
    )
    section_ids = [r[0] for r in sections_result.all()]

    if not section_ids:
        return {"message": "No sections found for student", "computed_count": 0}

    topics_result = await db.execute(
        select(Topic.id).where(Topic.section_id.in_(section_ids))
    )
    topic_ids = [r[0] for r in topics_result.all()]

    summary = await compute_bulk_and_propagate(
        db,
        UUID(body.student_id),
        topic_ids,
        signal_window_days=body.signal_window_days,
    )
    await db.commit()

    # Background remedial for all high-GI gaps
    background_tasks.add_task(
        _background_remedial_bulk,
        body.student_id,
    )

    return summary


async def _background_remedial_bulk(student_id: str):
    from app.database import async_session

    async with async_session() as db:
        try:
            await schedule_remedial_for_high_gi_gaps(db, UUID(student_id))
        except Exception as exc:
            logger.error("[BG] Bulk remedial generation failed: %s", exc)
            await db.rollback()


# ─────────────────────────────────────────────────────────────
# Gap retrieval
# ─────────────────────────────────────────────────────────────

@router.get("/student/{student_id}", response_model=list[StudentGapResponse])
async def list_student_gaps(
    student_id: str,
    topic_id: Optional[str] = Query(default=None),
    include_propagated: bool = Query(default=True),
    min_gi: Optional[float] = Query(default=None, ge=0, le=100),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return GI records for a student, with optional filters.

    Query params
    ------------
    topic_id           Filter to a single topic.
    include_propagated Include propagated-risk records (default True).
    min_gi             Only return gaps with GI ≥ min_gi.
    limit / offset     Pagination.

    Access: student, parent (own child), teacher, admin.
    """
    await _assert_can_access_student(current_user, student_id, db)

    where_clauses = [StudentGap.student_id == student_id]
    if topic_id:
        where_clauses.append(StudentGap.topic_id == topic_id)
    if not include_propagated:
        where_clauses.append(StudentGap.is_propagated_risk == False)
    if min_gi is not None:
        where_clauses.append(StudentGap.gap_index >= min_gi)

    result = await db.execute(
        select(StudentGap)
        .where(and_(*where_clauses))
        .order_by(StudentGap.gap_index.desc())
        .limit(limit)
        .offset(offset)
    )
    gaps = result.scalars().all()

    out: list[StudentGapResponse] = []
    for gap in gaps:
        topic = await db.get(Topic, gap.topic_id)
        out.append(_gap_to_response(gap, topic.title if topic else None))
    return out


@router.get("/student/{student_id}/{topic_id}", response_model=StudentGapResponse)
async def get_student_gap(
    student_id: str,
    topic_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the GI record for a specific (student, topic) pair."""
    await _assert_can_access_student(current_user, student_id, db)

    result = await db.execute(
        select(StudentGap).where(
            and_(
                StudentGap.student_id == student_id,
                StudentGap.topic_id == topic_id,
            )
        ).order_by(StudentGap.is_propagated_risk.asc())  # prefer direct record
    )
    gap = result.scalars().first()
    if not gap:
        raise HTTPException(status_code=404, detail="Gap record not found")

    topic = await db.get(Topic, gap.topic_id)
    return _gap_to_response(gap, topic.title if topic else None)


# ─────────────────────────────────────────────────────────────
# Remedial plan
# ─────────────────────────────────────────────────────────────

@router.post("/remedial/generate/{student_id}")
async def trigger_remedial_generation(
    student_id: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(check_ai_token_limit),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger LLM remedial plan generation for all high-GI gaps of a student
    that do not yet have a plan.

    This runs asynchronously via BackgroundTasks so the endpoint returns
    immediately with a count of pending gaps.

    Access: teacher, admin, school_admin.
    """
    if current_user.role not in (UserRole.TEACHER, UserRole.ADMIN, UserRole.SCHOOL_ADMIN):
        raise HTTPException(status_code=403, detail="Only teachers and admins can trigger remedial generation")

    # Count pending gaps (for the response)
    result = await db.execute(
        select(StudentGap).where(
            and_(
                StudentGap.student_id == student_id,
                StudentGap.gap_index > GI_THRESHOLD,
                StudentGap.remedial_plan.is_(None),
            )
        )
    )
    pending_gaps = result.scalars().all()

    background_tasks.add_task(_background_remedial_bulk, student_id)

    return {
        "message": "Remedial plan generation queued",
        "pending_gaps": len(pending_gaps),
    }


# ─────────────────────────────────────────────────────────────
# Topic prerequisites (DAG management)
# ─────────────────────────────────────────────────────────────

@router.post("/prerequisites", response_model=TopicPrerequisiteResponse, status_code=201)
async def add_prerequisite(
    body: TopicPrerequisiteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Add a prerequisite edge: ``prerequisite_topic_id`` → ``dependent_topic_id``.

    Access: teacher, admin, school_admin.
    """
    if current_user.role not in (UserRole.TEACHER, UserRole.ADMIN, UserRole.SCHOOL_ADMIN):
        raise HTTPException(status_code=403, detail="Only teachers and admins can manage prerequisites")

    # Validate both topics exist
    prereq_topic = await db.get(Topic, body.prerequisite_topic_id)
    dep_topic = await db.get(Topic, body.dependent_topic_id)
    if not prereq_topic:
        raise HTTPException(status_code=404, detail="Prerequisite topic not found")
    if not dep_topic:
        raise HTTPException(status_code=404, detail="Dependent topic not found")

    # Check for duplicates
    existing = await db.execute(
        select(TopicPrerequisite).where(
            and_(
                TopicPrerequisite.prerequisite_topic_id == body.prerequisite_topic_id,
                TopicPrerequisite.dependent_topic_id == body.dependent_topic_id,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Prerequisite edge already exists")

    edge = TopicPrerequisite(
        prerequisite_topic_id=body.prerequisite_topic_id,
        dependent_topic_id=body.dependent_topic_id,
    )
    db.add(edge)
    await db.flush()

    return TopicPrerequisiteResponse(
        id=str(edge.id),
        prerequisite_topic_id=str(edge.prerequisite_topic_id),
        prerequisite_topic_title=prereq_topic.title,
        dependent_topic_id=str(edge.dependent_topic_id),
        dependent_topic_title=dep_topic.title,
        created_at=edge.created_at.isoformat(),
    )


@router.delete("/prerequisites/{prerequisite_id}", status_code=204)
async def remove_prerequisite(
    prerequisite_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a prerequisite edge by its ID. Access: teacher, admin."""
    if current_user.role not in (UserRole.TEACHER, UserRole.ADMIN, UserRole.SCHOOL_ADMIN):
        raise HTTPException(status_code=403, detail="Only teachers and admins can manage prerequisites")

    edge = await db.get(TopicPrerequisite, prerequisite_id)
    if not edge:
        raise HTTPException(status_code=404, detail="Prerequisite edge not found")

    await db.delete(edge)
    await db.flush()


@router.get("/prerequisites/{topic_id}", response_model=list[TopicPrerequisiteResponse])
async def list_prerequisites(
    topic_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all prerequisite edges where ``topic_id`` is the *dependent* topic
    (i.e., topics that must be mastered before this one).
    """
    result = await db.execute(
        select(TopicPrerequisite).where(
            TopicPrerequisite.dependent_topic_id == topic_id
        )
    )
    edges = result.scalars().all()

    out: list[TopicPrerequisiteResponse] = []
    for edge in edges:
        prereq_topic = await db.get(Topic, edge.prerequisite_topic_id)
        dep_topic = await db.get(Topic, edge.dependent_topic_id)
        out.append(TopicPrerequisiteResponse(
            id=str(edge.id),
            prerequisite_topic_id=str(edge.prerequisite_topic_id),
            prerequisite_topic_title=prereq_topic.title if prereq_topic else None,
            dependent_topic_id=str(edge.dependent_topic_id),
            dependent_topic_title=dep_topic.title if dep_topic else None,
            created_at=edge.created_at.isoformat() if edge.created_at else None,
        ))
    return out


# ─────────────────────────────────────────────────────────────
# Signal ingestion endpoints
# ─────────────────────────────────────────────────────────────

@router.post("/signals/quiz", status_code=201)
async def ingest_quiz_response(
    body: QuizResponseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record a quiz response for GI signal computation."""
    row = QuizResponse(
        student_id=body.student_id,
        topic_id=body.topic_id,
        question_text=body.question_text,
        is_correct=body.is_correct,
        response_time_seconds=body.response_time_seconds,
        attempt_number=body.attempt_number,
    )
    db.add(row)
    await db.flush()
    return {"id": str(row.id), "message": "Quiz response recorded"}


@router.post("/signals/assignment", status_code=201)
async def ingest_assignment_submission(
    body: AssignmentSubmissionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record an assignment submission for GI signal computation."""
    row = AssignmentSubmission(
        student_id=body.student_id,
        topic_id=body.topic_id,
        raw_score=body.raw_score,
        max_score=body.max_score,
        is_missed=body.is_missed,
    )
    db.add(row)
    await db.flush()
    return {"id": str(row.id), "message": "Assignment submission recorded"}


@router.post("/signals/comprehension", status_code=201)
async def ingest_comprehension_score(
    body: ComprehensionScoreCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record a comprehension score evaluation for GI signal computation."""
    row = ComprehensionScore(
        student_id=body.student_id,
        topic_id=body.topic_id,
        score=body.score,
    )
    db.add(row)
    await db.flush()
    return {"id": str(row.id), "message": "Comprehension score recorded"}


@router.post("/signals/engagement", status_code=201)
async def ingest_engagement_event(
    body: EngagementEventCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record an engagement event for GI signal computation."""
    row = EngagementEvent(
        student_id=body.student_id,
        topic_id=body.topic_id,
        event_type=body.event_type,
    )
    db.add(row)
    await db.flush()
    return {"id": str(row.id), "message": "Engagement event recorded"}
