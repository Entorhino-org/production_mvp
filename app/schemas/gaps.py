"""
Pydantic schemas for Gap Analysis v2.0.

Covers:
  - Remedial plan validation (LLM output)
  - API request/response shapes for GI, signals, and propagated-risk records
  - Topic prerequisite management
"""

from __future__ import annotations

from typing import Any, Optional
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator


# ── Remedial Plan (LLM output validation) ────────────────────

class MCQOption(BaseModel):
    """Single option for a multiple-choice question."""
    label: str = Field(..., description="Option label, e.g. 'A', 'B', 'C', 'D'")
    text: str = Field(..., description="Option text")


class MicroQuizQuestion(BaseModel):
    """One MCQ in the 5-question micro-quiz."""
    question: str = Field(..., description="Question text")
    options: list[MCQOption] = Field(..., min_length=2, max_length=6)
    correct_label: str = Field(..., description="Label of the correct option")


class PracticeProblem(BaseModel):
    """One scaffolded practice problem (hints only, no answers)."""
    problem: str = Field(..., description="Problem statement")
    hints: list[str] = Field(..., min_length=1, description="Step-by-step hints")


class RemedialPlanSchema(BaseModel):
    """
    Validated structure for LLM-generated remedial content.

    All five components are required; the LLM output is rejected if any
    field is missing or does not conform to these types.
    """
    # ~200-word plain-language explanation (markdown)
    concept_reteach: str = Field(
        ...,
        min_length=20,
        description="Grade-level explanation of the concept (markdown, ~200 words)",
    )
    # 5 MCQs with increasing difficulty
    micro_quiz: list[MicroQuizQuestion] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="5 multiple-choice questions, foundational → advanced",
    )
    # Narrative story hook (markdown)
    story_hook: str = Field(
        ...,
        min_length=10,
        description="Relatable story wrapping the concept (markdown narrative)",
    )
    # 3 scaffolded problems
    practice_problems: list[PracticeProblem] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Scaffolded practice problems with hints (no answers)",
    )
    # Plain-text teacher alert
    teacher_alert: str = Field(
        ...,
        min_length=10,
        description="1-paragraph summary + intervention suggestion (plain text)",
    )


# ── Signal components response ────────────────────────────────

class GapSignalsResponse(BaseModel):
    """Per-signal component values that contributed to the GI."""
    quiz_score: Optional[float] = Field(None, ge=0, le=100)
    assignment_score: Optional[float] = Field(None, ge=0, le=100)
    comprehension_index: Optional[float] = Field(None, ge=0, le=100)
    engagement_depth_ratio: Optional[float] = Field(None, ge=0, le=1)
    peer_benchmark_normalized: Optional[float] = Field(None, ge=0, le=100)
    source_flags: Optional[dict[str, bool]] = None


# ── Student Gap response ──────────────────────────────────────

class StudentGapResponse(BaseModel):
    """Full GI record returned by the API."""
    id: str
    student_id: str
    topic_id: str
    topic_title: Optional[str] = None

    # Composite score
    gap_index: float = Field(..., ge=0, le=100, description="Gap Index [0–100]; higher = more critical")
    # Legacy alias (equals gap_index)
    gap_score: Optional[float] = None

    # Signal breakdown
    signals: GapSignalsResponse

    # Computation metadata
    computed_at: Optional[str] = None
    signal_window_days: int = 90

    # Propagation metadata
    is_propagated_risk: bool = False
    propagated_from_topic_id: Optional[str] = None
    propagated_from_topic_title: Optional[str] = None
    propagation_depth: int = 0
    propagation_decay_factor: float = 0.7

    # Remedial plan (present only when GI > threshold and generation succeeded)
    remedial_plan: Optional[dict[str, Any]] = None

    status: str = "open"
    created_at: Optional[str] = None


# ── Compute / trigger request ─────────────────────────────────

class ComputeGIRequest(BaseModel):
    """Request body to trigger GI computation for a student + topic."""
    student_id: str
    topic_id: str
    signal_window_days: int = Field(default=90, ge=1, le=365)


class BulkComputeGIRequest(BaseModel):
    """Request body to trigger GI computation for all topics of a student."""
    student_id: str
    signal_window_days: int = Field(default=90, ge=1, le=365)


# ── Topic prerequisite schemas ────────────────────────────────

class TopicPrerequisiteCreate(BaseModel):
    """Create a prerequisite edge in the topic DAG."""
    prerequisite_topic_id: str = Field(..., description="Topic that must be mastered first")
    dependent_topic_id: str = Field(..., description="Topic that depends on the prerequisite")

    @model_validator(mode="after")
    def _no_self_loop(self) -> "TopicPrerequisiteCreate":
        if self.prerequisite_topic_id == self.dependent_topic_id:
            raise ValueError("A topic cannot be its own prerequisite")
        return self


class TopicPrerequisiteResponse(BaseModel):
    """Returned prerequisite edge."""
    id: str
    prerequisite_topic_id: str
    prerequisite_topic_title: Optional[str] = None
    dependent_topic_id: str
    dependent_topic_title: Optional[str] = None
    created_at: Optional[str] = None


# ── Quiz / Assignment / Comprehension / Engagement ingestion ──

class QuizResponseCreate(BaseModel):
    student_id: str
    topic_id: str
    question_text: Optional[str] = None
    is_correct: bool
    response_time_seconds: Optional[float] = Field(None, ge=0)
    attempt_number: int = Field(default=1, ge=1)


class AssignmentSubmissionCreate(BaseModel):
    student_id: str
    topic_id: str
    raw_score: Optional[float] = Field(None, ge=0)
    max_score: float = Field(default=100.0, gt=0)
    is_missed: bool = False

    @model_validator(mode="after")
    def _score_required_when_not_missed(self) -> "AssignmentSubmissionCreate":
        if not self.is_missed and self.raw_score is None:
            raise ValueError("raw_score is required when is_missed is False")
        return self


class ComprehensionScoreCreate(BaseModel):
    student_id: str
    topic_id: str
    score: float = Field(..., ge=0, le=100)


class EngagementEventCreate(BaseModel):
    student_id: str
    topic_id: str
    event_type: str = Field(..., min_length=1, max_length=50)
