"""
Gap Analysis v2.0 — composite Gap Index (GI) computation service.

Architecture
------------
Signal computation is fully synchronous / pure-Python arithmetic so that
it can be unit-tested without a database.  The async ``compute_and_persist``
entry-point handles DB I/O and wires everything together.

Tuning knobs (change here, nowhere else)
-----------------------------------------
GI_THRESHOLD            = 60    Gaps above this trigger propagation + remediation
PROPAGATION_DECAY       = 0.7   Propagated GI = parent_GI × decay
SIGNAL_WINDOW_DAYS      = 90    Default look-back window for signal queries
EWM_SPAN                = 5     Exponential-window span for comprehension signal
RECENT_QUIZ_WEIGHT      = 2.0   Recency multiplier for the latest quiz attempt
LATENCY_PENALTY_SECONDS = 120   Responses taking longer than this are penalised
MAX_LATENCY_PENALTY     = 0.15  Maximum fractional score reduction from latency
MISSED_SUBMISSION_SCORE = 0.0   Score awarded to missed assignments
"""

from __future__ import annotations

import logging
import math
from collections import deque
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gaps import (
    AssignmentSubmission,
    ComprehensionScore,
    EngagementEvent,
    QuizResponse,
    StudentGap,
    TopicPrerequisite,
)
from app.models.academic import Topic

logger = logging.getLogger(__name__)

# ── Tuning knobs ──────────────────────────────────────────────
GI_THRESHOLD: float = 60.0
PROPAGATION_DECAY: float = 0.7
SIGNAL_WINDOW_DAYS: int = 90
EWM_SPAN: int = 5
RECENT_QUIZ_WEIGHT: float = 2.0
LATENCY_PENALTY_SECONDS: float = 120.0
MAX_LATENCY_PENALTY: float = 0.15
MISSED_SUBMISSION_SCORE: float = 0.0

# ── Signal weights (must sum to 1.0) ──────────────────────────
W_QUIZ = 0.35
W_ASSIGNMENT = 0.25
W_COMPREHENSION = 0.20
W_ENGAGEMENT = 0.10
W_PEER = 0.10


# ─────────────────────────────────────────────────────────────
# Pure-Python signal computation functions
# (all return values in [0, 100] unless noted)
# ─────────────────────────────────────────────────────────────

def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    """Clamp a value into [lo, hi]."""
    return max(lo, min(hi, value))


def compute_quiz_score(
    responses: list[dict],
    *,
    recent_weight: float = RECENT_QUIZ_WEIGHT,
    latency_penalty_seconds: float = LATENCY_PENALTY_SECONDS,
    max_latency_penalty: float = MAX_LATENCY_PENALTY,
) -> tuple[float, bool]:
    """
    Compute *Quiz Performance* signal [0–100].

    Weighting rules
    ---------------
    - The **most recent attempt** gets ``recent_weight × 1.0`` weight;
      all earlier attempts get ``1.0`` weight.
    - Latency penalty: responses slower than ``latency_penalty_seconds``
      have their correctness score reduced by up to ``max_latency_penalty``
      proportionally.

    Parameters
    ----------
    responses : list of dicts with keys:
        is_correct (bool), response_time_seconds (float | None),
        attempt_number (int), answered_at (datetime)

    Returns
    -------
    (score_0_to_100, has_data)
    """
    if not responses:
        return 50.0, False  # Default / neutral when no data

    # Sort by answered_at ascending so last element = most recent
    sorted_responses = sorted(responses, key=lambda r: r.get("answered_at", datetime.min))

    total_weight = 0.0
    weighted_sum = 0.0

    for i, resp in enumerate(sorted_responses):
        is_recent = i == len(sorted_responses) - 1
        weight = recent_weight if is_recent else 1.0

        correctness = 1.0 if resp.get("is_correct") else 0.0

        # Latency penalty
        rt = resp.get("response_time_seconds")
        if rt is not None and rt > latency_penalty_seconds:
            excess = rt - latency_penalty_seconds
            # Penalty grows with excess time, capped at max_latency_penalty
            penalty = min(max_latency_penalty, (excess / latency_penalty_seconds) * max_latency_penalty)
            correctness = max(0.0, correctness - penalty)

        weighted_sum += weight * correctness
        total_weight += weight

    if total_weight == 0:
        return 50.0, False

    score = (weighted_sum / total_weight) * 100.0
    return _clamp(score), True


def compute_assignment_score(
    submissions: list[dict],
    class_median: float = 50.0,
    *,
    missed_score: float = MISSED_SUBMISSION_SCORE,
) -> tuple[float, bool]:
    """
    Compute *Assignment Score* signal [0–100].

    Method
    ------
    1. Normalise each submission: ``norm = raw_score / max_score × 100``.
    2. Missed submissions count as ``missed_score`` (default 0).
    3. Return the mean normalised score delta from class median, rescaled
       to [0, 100].  When there are no submissions, return 50 (neutral).

    Parameters
    ----------
    submissions : list of dicts with keys:
        raw_score (float | None), max_score (float), is_missed (bool)
    class_median : class median normalised score [0–100]
    """
    if not submissions:
        return 50.0, False

    normalised_scores: list[float] = []
    for sub in submissions:
        if sub.get("is_missed"):
            normalised_scores.append(missed_score)
        else:
            raw = sub.get("raw_score")
            max_s = sub.get("max_score") or 100.0
            if raw is None:
                normalised_scores.append(missed_score)
            else:
                normalised_scores.append(_clamp((raw / max_s) * 100.0))

    if not normalised_scores:
        return 50.0, False

    student_mean = sum(normalised_scores) / len(normalised_scores)
    # Adjust for class median: student_mean near class_median → score 50
    delta = student_mean - class_median  # range roughly [-100, +100]
    # Map to [0, 100]: perfect student → 100, worst → 0
    score = _clamp(50.0 + delta * 0.5)
    return score, True


def compute_comprehension_index(
    scores: list[dict],
    *,
    span: int = EWM_SPAN,
) -> tuple[float, bool]:
    """
    Compute *Comprehension Index* signal [0–100].

    Uses an exponentially-weighted mean (EWM) over the last ``span``
    evaluations, most-recent highest weight.

    Parameters
    ----------
    scores : list of dicts with keys: score (float [0–100]), evaluated_at (datetime)
    span   : EWM span (α = 2 / (span + 1))
    """
    if not scores:
        return 50.0, False

    # Take last `span` evaluations sorted chronologically
    sorted_scores = sorted(scores, key=lambda s: s.get("evaluated_at", datetime.min))
    window = sorted_scores[-span:]

    alpha = 2.0 / (span + 1)
    ewm = window[0].get("score", 50.0)
    for entry in window[1:]:
        ewm = alpha * entry.get("score", ewm) + (1 - alpha) * ewm

    return _clamp(ewm), True


def compute_engagement_depth(
    events: list[dict],
) -> tuple[float, bool]:
    """
    Compute *Engagement Depth Ratio* [0–1].

    Ratio of replay/re-read events to total events.  High ratio signals
    poor comprehension; this is used as ``(1 - ratio)`` in the GI formula
    so that high ratio → high GI contribution.

    Returns (ratio [0–1], has_data)
    """
    if not events:
        return 0.5, False  # Default: mid-range when no data

    total = len(events)
    replay_types = {"replay", "reread", "re-read", "seek_back"}
    replay_count = sum(1 for e in events if e.get("event_type", "").lower() in replay_types)

    ratio = replay_count / total
    return max(0.0, min(1.0, ratio)), True


def compute_peer_benchmark(
    student_score: float,
    class_scores: list[float],
) -> tuple[float, bool]:
    """
    Compute *Peer Benchmark* signal [0–100].

    Calculates z-score of ``student_score`` vs ``class_scores`` and maps
    the result to [0, 100]:
      - z = +2 (top of class) → 100
      - z =  0 (class mean)   →  50
      - z = -2 (bottom)       →   0

    Parameters
    ----------
    student_score : student's normalised score [0–100]
    class_scores  : list of all students' normalised scores [0–100]
    """
    if not class_scores or len(class_scores) < 2:
        return 50.0, False

    n = len(class_scores)
    mean = sum(class_scores) / n
    variance = sum((x - mean) ** 2 for x in class_scores) / n
    std = math.sqrt(variance)

    if std < 1e-9:
        # All students scored the same
        return 50.0, False

    z = (student_score - mean) / std
    # Map z ∈ [-3, +3] → [0, 100]
    normalised = _clamp(50.0 + z * (50.0 / 2.0))
    return normalised, True


def compute_gap_index(
    quiz_score: float,
    assignment_score: float,
    comprehension_index: float,
    engagement_depth_ratio: float,
    peer_benchmark_normalized: float,
) -> float:
    """
    Composite Gap Index formula.

    GI = 100 − (
          0.35 × QuizScore
        + 0.25 × AssignmentScore
        + 0.20 × ComprehensionIndex
        + 0.10 × (1 − EngagementDepthRatio × 100)
        + 0.10 × NormalisedPeerBenchmark
    )

    All inputs must be in [0, 100] except engagement_depth_ratio which
    is in [0, 1].

    Returns GI ∈ [0, 100].
    """
    engagement_contribution = (1.0 - engagement_depth_ratio) * 100.0
    weighted_mastery = (
        W_QUIZ * quiz_score
        + W_ASSIGNMENT * assignment_score
        + W_COMPREHENSION * comprehension_index
        + W_ENGAGEMENT * engagement_contribution
        + W_PEER * peer_benchmark_normalized
    )
    gi = 100.0 - weighted_mastery
    return _clamp(gi)


# ─────────────────────────────────────────────────────────────
# Async DB-backed helpers
# ─────────────────────────────────────────────────────────────

async def _fetch_quiz_responses(
    db: AsyncSession,
    student_id: UUID,
    topic_id: UUID,
    since: datetime,
) -> list[dict]:
    """Fetch quiz responses for a (student, topic) within the signal window."""
    result = await db.execute(
        select(QuizResponse).where(
            and_(
                QuizResponse.student_id == student_id,
                QuizResponse.topic_id == topic_id,
                QuizResponse.answered_at >= since,
            )
        ).order_by(QuizResponse.answered_at.asc())
    )
    rows = result.scalars().all()
    return [
        {
            "is_correct": r.is_correct,
            "response_time_seconds": r.response_time_seconds,
            "attempt_number": r.attempt_number,
            "answered_at": r.answered_at,
        }
        for r in rows
    ]


async def _fetch_assignment_submissions(
    db: AsyncSession,
    student_id: UUID,
    topic_id: UUID,
    since: datetime,
) -> tuple[list[dict], float]:
    """
    Fetch assignment submissions and compute class median for the topic.

    Returns (student_submissions, class_median_normalised_score).
    """
    # Student's submissions
    student_result = await db.execute(
        select(AssignmentSubmission).where(
            and_(
                AssignmentSubmission.student_id == student_id,
                AssignmentSubmission.topic_id == topic_id,
                AssignmentSubmission.created_at >= since,
            )
        )
    )
    student_rows = student_result.scalars().all()
    student_subs = [
        {
            "raw_score": r.raw_score,
            "max_score": r.max_score,
            "is_missed": r.is_missed,
        }
        for r in student_rows
    ]

    # Class median: all non-missed submissions for this topic
    class_result = await db.execute(
        select(
            AssignmentSubmission.raw_score,
            AssignmentSubmission.max_score,
        ).where(
            and_(
                AssignmentSubmission.topic_id == topic_id,
                AssignmentSubmission.is_missed == False,
                AssignmentSubmission.created_at >= since,
                AssignmentSubmission.raw_score.isnot(None),
            )
        )
    )
    class_normalised: list[float] = []
    for raw, max_s in class_result.all():
        if max_s and max_s > 0:
            class_normalised.append(_clamp((raw / max_s) * 100.0))

    class_median = 50.0
    if class_normalised:
        sorted_scores = sorted(class_normalised)
        mid = len(sorted_scores) // 2
        if len(sorted_scores) % 2 == 0:
            class_median = (sorted_scores[mid - 1] + sorted_scores[mid]) / 2.0
        else:
            class_median = sorted_scores[mid]

    return student_subs, class_median


async def _fetch_comprehension_scores(
    db: AsyncSession,
    student_id: UUID,
    topic_id: UUID,
    since: datetime,
) -> list[dict]:
    result = await db.execute(
        select(ComprehensionScore).where(
            and_(
                ComprehensionScore.student_id == student_id,
                ComprehensionScore.topic_id == topic_id,
                ComprehensionScore.evaluated_at >= since,
            )
        ).order_by(ComprehensionScore.evaluated_at.asc())
    )
    rows = result.scalars().all()
    return [{"score": r.score, "evaluated_at": r.evaluated_at} for r in rows]


async def _fetch_engagement_events(
    db: AsyncSession,
    student_id: UUID,
    topic_id: UUID,
    since: datetime,
) -> list[dict]:
    result = await db.execute(
        select(EngagementEvent).where(
            and_(
                EngagementEvent.student_id == student_id,
                EngagementEvent.topic_id == topic_id,
                EngagementEvent.occurred_at >= since,
            )
        )
    )
    rows = result.scalars().all()
    return [{"event_type": r.event_type} for r in rows]


async def _fetch_peer_scores(
    db: AsyncSession,
    topic_id: UUID,
    since: datetime,
) -> list[float]:
    """Aggregate per-student assignment scores for the peer benchmark."""
    result = await db.execute(
        select(
            AssignmentSubmission.student_id,
            func.avg(AssignmentSubmission.raw_score / AssignmentSubmission.max_score * 100),
        ).where(
            and_(
                AssignmentSubmission.topic_id == topic_id,
                AssignmentSubmission.is_missed == False,
                AssignmentSubmission.created_at >= since,
                AssignmentSubmission.raw_score.isnot(None),
                AssignmentSubmission.max_score > 0,
            )
        ).group_by(AssignmentSubmission.student_id)
    )
    return [float(avg) for _, avg in result.all() if avg is not None]


# ─────────────────────────────────────────────────────────────
# Main async compute + persist
# ─────────────────────────────────────────────────────────────

async def compute_and_persist(
    db: AsyncSession,
    student_id: UUID,
    topic_id: UUID,
    *,
    signal_window_days: int = SIGNAL_WINDOW_DAYS,
) -> StudentGap:
    """
    Compute the composite GI for (student_id, topic_id) and upsert the
    result into ``student_gaps``.

    The function fetches all five signal sources, computes each component,
    applies the weighted GI formula, and either creates or updates the
    existing StudentGap row.  It also sets ``gap_score`` to ``gap_index``
    for backward compatibility.

    Parameters
    ----------
    db                 : async SQLAlchemy session
    student_id         : UUID of the student
    topic_id           : UUID of the topic
    signal_window_days : look-back window for all signal queries
    """
    since = datetime.utcnow() - timedelta(days=signal_window_days)

    # ── Fetch signals ─────────────────────────────────────────
    quiz_data = await _fetch_quiz_responses(db, student_id, topic_id, since)
    sub_data, class_median = await _fetch_assignment_submissions(db, student_id, topic_id, since)
    comp_data = await _fetch_comprehension_scores(db, student_id, topic_id, since)
    eng_data = await _fetch_engagement_events(db, student_id, topic_id, since)
    peer_scores = await _fetch_peer_scores(db, topic_id, since)

    # ── Compute signals ───────────────────────────────────────
    quiz_score, quiz_has_data = compute_quiz_score(quiz_data)
    assignment_score, assign_has_data = compute_assignment_score(sub_data, class_median)
    comprehension_index, comp_has_data = compute_comprehension_index(comp_data)
    engagement_depth_ratio, engage_has_data = compute_engagement_depth(eng_data)

    # For peer benchmark, compute student's own mean normalised assignment score
    student_topic_scores = [
        _clamp((s["raw_score"] / s["max_score"]) * 100.0)
        for s in sub_data
        if not s.get("is_missed") and s.get("raw_score") is not None and s.get("max_score")
    ]
    student_mean = sum(student_topic_scores) / len(student_topic_scores) if student_topic_scores else 50.0
    peer_benchmark_normalized, peer_has_data = compute_peer_benchmark(student_mean, peer_scores)

    # ── Composite GI ──────────────────────────────────────────
    gap_index = compute_gap_index(
        quiz_score,
        assignment_score,
        comprehension_index,
        engagement_depth_ratio,
        peer_benchmark_normalized,
    )

    source_flags = {
        "quiz": quiz_has_data,
        "assignment": assign_has_data,
        "comprehension": comp_has_data,
        "engagement": engage_has_data,
        "peer": peer_has_data,
    }

    # ── Upsert StudentGap row ─────────────────────────────────
    existing_result = await db.execute(
        select(StudentGap).where(
            and_(
                StudentGap.student_id == student_id,
                StudentGap.topic_id == topic_id,
                StudentGap.is_propagated_risk == False,
            )
        )
    )
    gap = existing_result.scalar_one_or_none()

    if gap is None:
        gap = StudentGap(
            student_id=student_id,
            topic_id=topic_id,
        )
        db.add(gap)

    gap.gap_index = round(gap_index, 4)
    gap.gap_score = round(gap_index, 4)  # legacy alias
    gap.quiz_score = round(quiz_score, 4)
    gap.assignment_score = round(assignment_score, 4)
    gap.comprehension_index = round(comprehension_index, 4)
    gap.engagement_depth_ratio = round(engagement_depth_ratio, 6)
    gap.peer_benchmark_normalized = round(peer_benchmark_normalized, 4)
    gap.computed_at = datetime.utcnow()
    gap.signal_window_days = signal_window_days
    gap.source_flags = source_flags
    gap.is_propagated_risk = False
    gap.propagation_depth = 0

    await db.flush()
    logger.info(
        "[GI] student=%s topic=%s GI=%.1f (quiz=%.1f assign=%.1f comp=%.1f engage=%.3f peer=%.1f)",
        student_id, topic_id, gap_index,
        quiz_score, assignment_score, comprehension_index,
        engagement_depth_ratio, peer_benchmark_normalized,
    )
    return gap


# ─────────────────────────────────────────────────────────────
# Prerequisite propagation
# ─────────────────────────────────────────────────────────────

async def propagate_risks(
    db: AsyncSession,
    student_id: UUID,
    *,
    gi_threshold: float = GI_THRESHOLD,
    decay: float = PROPAGATION_DECAY,
    max_depth: int = 10,
) -> list[StudentGap]:
    """
    BFS propagation of high-GI risk through the prerequisite DAG.

    Algorithm
    ---------
    1. Load all directly-computed (non-propagated) StudentGap rows for
       this student.
    2. Identify "seed" topics where GI > gi_threshold.
    3. BFS from each seed along the prerequisite graph's *dependent*
       direction:  ``prerequisite → dependent`` means if you fail the
       prerequisite topic, dependent topics are also at risk.
    4. For each unvisited dependent topic that lacks a real GI record,
       create a propagated-risk StudentGap with:
           propagated_GI = parent_GI × decay
    5. Track visited (topic_id, depth) pairs to prevent duplicates and
       avoid cycles caused by bad data.

    Returns
    -------
    List of upserted propagated StudentGap rows.
    """
    # ── Load all assessed topics for this student ─────────────
    assessed_result = await db.execute(
        select(StudentGap).where(
            and_(
                StudentGap.student_id == student_id,
                StudentGap.is_propagated_risk == False,
            )
        )
    )
    assessed_gaps: dict[UUID, StudentGap] = {
        g.topic_id: g for g in assessed_result.scalars().all()
    }

    # ── Load the full prerequisite DAG ───────────────────────
    prereq_result = await db.execute(select(TopicPrerequisite))
    prereq_rows = prereq_result.scalars().all()

    # Build adjacency: prereq_topic_id → list[dependent_topic_id]
    prereq_to_dependents: dict[UUID, list[UUID]] = {}
    for edge in prereq_rows:
        prereq_to_dependents.setdefault(edge.prerequisite_topic_id, []).append(
            edge.dependent_topic_id
        )

    # ── BFS from high-GI seeds ────────────────────────────────
    # Queue items: (topic_id, parent_gi, depth, origin_topic_id)
    queue: deque[tuple[UUID, float, int, UUID]] = deque()

    for topic_id, gap in assessed_gaps.items():
        if gap.gap_index > gi_threshold:
            queue.append((topic_id, gap.gap_index, 0, topic_id))

    visited: set[UUID] = set(assessed_gaps.keys())
    propagated_gaps: list[StudentGap] = []

    while queue:
        current_topic_id, parent_gi, depth, origin_id = queue.popleft()

        if depth >= max_depth:
            continue

        for dependent_id in prereq_to_dependents.get(current_topic_id, []):
            if dependent_id in visited:
                continue
            visited.add(dependent_id)

            propagated_gi = _clamp(parent_gi * decay)

            # Upsert propagated StudentGap
            existing_result = await db.execute(
                select(StudentGap).where(
                    and_(
                        StudentGap.student_id == student_id,
                        StudentGap.topic_id == dependent_id,
                        StudentGap.is_propagated_risk == True,
                    )
                )
            )
            prop_gap = existing_result.scalar_one_or_none()

            if prop_gap is None:
                prop_gap = StudentGap(
                    student_id=student_id,
                    topic_id=dependent_id,
                )
                db.add(prop_gap)

            prop_gap.gap_index = round(propagated_gi, 4)
            prop_gap.gap_score = round(propagated_gi, 4)
            prop_gap.is_propagated_risk = True
            prop_gap.propagated_from_topic_id = origin_id
            prop_gap.propagation_depth = depth + 1
            prop_gap.propagation_decay_factor = decay
            prop_gap.computed_at = datetime.utcnow()
            prop_gap.source_flags = {"propagated": True}

            propagated_gaps.append(prop_gap)
            logger.info(
                "[PROPAGATE] student=%s topic=%s propagated_GI=%.1f depth=%d origin=%s",
                student_id, dependent_id, propagated_gi, depth + 1, origin_id,
            )

            # Continue BFS if propagated GI is still above threshold
            if propagated_gi > gi_threshold:
                queue.append((dependent_id, propagated_gi, depth + 1, origin_id))

    await db.flush()
    return propagated_gaps


async def compute_bulk_and_propagate(
    db: AsyncSession,
    student_id: UUID,
    topic_ids: list[UUID],
    *,
    signal_window_days: int = SIGNAL_WINDOW_DAYS,
) -> dict:
    """
    Compute GI for all given topics, then run prerequisite propagation.

    Returns a summary dict.
    """
    computed: list[StudentGap] = []
    for topic_id in topic_ids:
        try:
            gap = await compute_and_persist(db, student_id, topic_id, signal_window_days=signal_window_days)
            computed.append(gap)
        except Exception as exc:
            logger.warning("[GI] Failed for topic=%s: %s", topic_id, exc)

    propagated = await propagate_risks(db, student_id)

    high_gi_count = sum(1 for g in computed if g.gap_index > GI_THRESHOLD)
    return {
        "computed_count": len(computed),
        "propagated_count": len(propagated),
        "high_gi_count": high_gi_count,
    }
