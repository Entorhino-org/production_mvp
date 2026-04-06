"""
Gap Analysis v2.0 models — composite Gap Index (GI) with multi-signal fusion,
prerequisite DAG, and LLM-backed remedial plan storage.

Signal weights:
  Quiz Performance       35%  (quiz_responses)
  Assignment Score       25%  (assignment_submissions)
  Comprehension Index    20%  (comprehension_scores)
  Engagement Depth       10%  (engagement_events)
  Peer Benchmark         10%  (leaderboard z-score)

GI formula:
  GI = 100 - (
        0.35 * quiz_score
      + 0.25 * assignment_score
      + 0.20 * comprehension_index
      + 0.10 * (1 - engagement_depth_ratio)
      + 0.10 * peer_benchmark_normalized
  )
  GI ≈ 100 → critical gap  |  GI ≈ 0 → mastered

Tuning knobs:
  GI_THRESHOLD        = 60    (above this triggers propagation + remediation)
  PROPAGATION_DECAY   = 0.7   (propagated GI = parent_GI * decay)
  SIGNAL_WINDOW_DAYS  = 90    (default lookback window for signal computation)
  EWM_SPAN            = 5     (exponential window span for comprehension EWM)
  RECENT_QUIZ_WEIGHT  = 2.0   (recency multiplier for latest quiz attempt)
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Index, Integer, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


# ── Signal source tables ──────────────────────────────────────

class QuizResponse(Base):
    """
    Individual student response to a quiz question linked to a topic.

    Used by the GI computation to derive *Quiz Performance* (35%).
    Recent attempts are weighted 2× by the service layer.
    """
    __tablename__ = "quiz_responses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    question_text = Column(Text, nullable=True)
    is_correct = Column(Boolean, nullable=False, default=False)
    # Time taken to answer in seconds; used for latency penalty
    response_time_seconds = Column(Float, nullable=True)
    # Attempt number within the same quiz session (1 = first)
    attempt_number = Column(Integer, nullable=False, default=1)
    answered_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    student = relationship("User", foreign_keys=[student_id])
    topic = relationship("Topic")

    __table_args__ = (
        Index("ix_quiz_responses_student_topic", "student_id", "topic_id"),
        Index("ix_quiz_responses_answered_at", "answered_at"),
    )


class AssignmentSubmission(Base):
    """
    Rubric-scored assignment submission linked to a topic.

    Used by the GI computation to derive *Assignment Score* (25%).
    ``is_missed=True`` records are penalised in the service layer.
    """
    __tablename__ = "assignment_submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    # Raw score awarded; NULL when is_missed=True
    raw_score = Column(Float, nullable=True)
    # Maximum possible score for rubric normalisation
    max_score = Column(Float, nullable=False, default=100.0)
    # True when the student did not submit
    is_missed = Column(Boolean, nullable=False, default=False)
    submitted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    student = relationship("User", foreign_keys=[student_id])
    topic = relationship("Topic")

    __table_args__ = (
        Index("ix_assignment_submissions_student_topic", "student_id", "topic_id"),
    )


class ComprehensionScore(Base):
    """
    Teacher- or AI-evaluated comprehension score for a student on a topic.

    Used by the GI computation to derive *Comprehension Index* (20%)
    via an exponentially-weighted mean over the last 5 evaluations.
    """
    __tablename__ = "comprehension_scores"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    # Score on a 0–100 scale
    score = Column(Float, nullable=False)
    evaluated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    student = relationship("User", foreign_keys=[student_id])
    topic = relationship("Topic")

    __table_args__ = (
        Index("ix_comprehension_scores_student_topic", "student_id", "topic_id"),
        Index("ix_comprehension_scores_evaluated_at", "evaluated_at"),
    )


class EngagementEvent(Base):
    """
    Learning-platform engagement event (e.g. video replay, re-read, first-view).

    Used by the GI computation to derive *Engagement Depth* (10%).
    A high ratio of replay/re-read events signals lower comprehension.

    Common event_type values:
      "view"        — first content view
      "replay"      — video replay
      "reread"      — article/notes re-read
      "pause"       — video pause
      "seek"        — video seek backward/forward
    """
    __tablename__ = "engagement_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(50), nullable=False)
    occurred_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    student = relationship("User", foreign_keys=[student_id])
    topic = relationship("Topic")

    __table_args__ = (
        Index("ix_engagement_events_student_topic", "student_id", "topic_id"),
    )


# ── Prerequisite DAG ──────────────────────────────────────────

class TopicPrerequisite(Base):
    """
    Directed edge in the topic prerequisite DAG.

    Edge meaning: ``prerequisite_topic_id`` must be mastered before
    ``dependent_topic_id``.  The GI propagation algorithm traverses
    this graph to flag dependent topics as 'propagated-risk' when
    a foundational topic has GI > threshold.
    """
    __tablename__ = "topic_prerequisites"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # The topic that must come first (parent / foundational topic)
    prerequisite_topic_id = Column(
        UUID(as_uuid=True),
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
    )
    # The topic that depends on the prerequisite (downstream / dependent)
    dependent_topic_id = Column(
        UUID(as_uuid=True),
        ForeignKey("topics.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    prerequisite_topic = relationship("Topic", foreign_keys=[prerequisite_topic_id])
    dependent_topic = relationship("Topic", foreign_keys=[dependent_topic_id])

    __table_args__ = (
        UniqueConstraint(
            "prerequisite_topic_id",
            "dependent_topic_id",
            name="uq_topic_prerequisite_edge",
        ),
        # Fast lookup: "what does topic X depend on?"
        Index("ix_topic_prerequisites_dependent", "dependent_topic_id"),
        # Fast lookup: "what topics require topic X as a prerequisite?"
        Index("ix_topic_prerequisites_prerequisite", "prerequisite_topic_id"),
    )


# ── Composite Gap Index ───────────────────────────────────────

class StudentGap(Base):
    """
    Composite Gap Index (GI) record for a (student, topic) pair.

    One row per (student_id, topic_id) — upserted on each recomputation.

    Backward-compatibility note:
      ``gap_score`` mirrors the legacy v1 field and equals ``gap_index``
      so old consumers reading ``gap_score`` continue to work.

    Fields
    ------
    gap_index               Composite GI [0–100]; high = critical gap.
    quiz_score              Quiz-performance component [0–100].
    assignment_score        Assignment-score component [0–100].
    comprehension_index     Comprehension-index component [0–100].
    engagement_depth_ratio  Engagement-depth ratio [0–1]; high = low
                            comprehension.
    peer_benchmark_normalized  Z-score normalised to [0–100].
    computed_at             Timestamp of last GI computation.
    signal_window_days      Lookback window used during computation.
    source_flags            JSON object recording which signals had data
                            (e.g. {"quiz": true, "assignment": false}).
    is_propagated_risk      True when GI was inferred via DAG propagation.
    propagated_from_topic_id  The direct parent topic that triggered
                            propagation.
    propagation_depth       Hops from the origin high-GI topic.
    propagation_decay_factor  Decay applied (default 0.7 per hop).
    remedial_plan           JSONB payload from LLM (validated by Pydantic
                            before storage).
    gap_score               Legacy alias for gap_index.
    """
    __tablename__ = "student_gaps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)

    # ── Composite GI ──────────────────────────────────────────
    gap_index = Column(Float, nullable=False, default=0.0)

    # ── Per-signal components (all 0–100 unless noted) ────────
    quiz_score = Column(Float, nullable=True)
    assignment_score = Column(Float, nullable=True)
    comprehension_index = Column(Float, nullable=True)
    engagement_depth_ratio = Column(Float, nullable=True)   # 0–1
    peer_benchmark_normalized = Column(Float, nullable=True)

    # ── Computation metadata ──────────────────────────────────
    computed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    signal_window_days = Column(Integer, nullable=False, default=90)
    # Records which signals had real data vs. defaults
    source_flags = Column(JSONB, nullable=True)

    # ── Propagated-risk fields ────────────────────────────────
    is_propagated_risk = Column(Boolean, nullable=False, default=False)
    propagated_from_topic_id = Column(
        UUID(as_uuid=True),
        ForeignKey("topics.id", ondelete="SET NULL"),
        nullable=True,
    )
    propagation_depth = Column(Integer, nullable=False, default=0)
    propagation_decay_factor = Column(Float, nullable=False, default=0.7)

    # ── Remedial plan (LLM output) ────────────────────────────
    remedial_plan = Column(JSONB, nullable=True)

    # ── Lifecycle ─────────────────────────────────────────────
    status = Column(String(20), nullable=False, default="open")   # open / resolved
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # ── Legacy backward-compatibility alias ───────────────────
    # Old consumers that read gap_score still work; it equals gap_index.
    gap_score = Column(Float, nullable=True)

    # ── Relationships ─────────────────────────────────────────
    student = relationship("User", foreign_keys=[student_id])
    topic = relationship("Topic", foreign_keys=[topic_id])
    propagated_from_topic = relationship("Topic", foreign_keys=[propagated_from_topic_id])

    __table_args__ = (
        UniqueConstraint("student_id", "topic_id", name="uq_student_gap_topic"),
        Index("ix_student_gaps_student_id", "student_id"),
        Index("ix_student_gaps_topic_id", "topic_id"),
        Index("ix_student_gaps_gap_index", "gap_index"),
    )
