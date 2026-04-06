"""
Gap Analysis v2.0 — LLM-backed remedial plan generation service.

When a student's Gap Index (GI) exceeds the threshold (default 60), this
service fires a structured prompt to the configured LLM (Claude / GPT-4o /
Gemini via OpenRouter), validates the JSON output with Pydantic, and persists
the result in ``student_gaps.remedial_plan``.

Integration pattern
--------------------
Use FastAPI's ``BackgroundTasks`` to invoke ``schedule_remedial_generation``
so that the GI compute endpoint returns immediately.

Remedial plan structure (validated by ``RemedialPlanSchema``):
  concept_reteach      markdown ~200 words, grade-level plain English
  micro_quiz           5 MCQs JSON array
  story_hook           markdown narrative
  practice_problems    3 scaffolded problems with hints (no answers)
  teacher_alert        plain-text summary + intervention suggestion
"""

from __future__ import annotations

import json
import logging
from typing import Optional
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gaps import StudentGap
from app.models.academic import Topic
from app.schemas.gaps import RemedialPlanSchema
from app.services.gap_analysis import GI_THRESHOLD

logger = logging.getLogger(__name__)

# Maximum tokens allocated for remedial plan generation
REMEDIAL_MAX_TOKENS = 3000


def _build_system_prompt() -> str:
    return (
        "You are an expert educational content designer specialised in K–12 learning gaps.\n"
        "You will receive a student's topic name and Gap Index (GI) score.\n"
        "Your task is to produce a structured remedial plan in valid JSON format.\n\n"
        "The JSON must have exactly these top-level keys:\n"
        "  concept_reteach  : string (markdown, ~200 words, plain-language explanation)\n"
        "  micro_quiz       : array of 5 MCQ objects, each with:\n"
        "                       question: string\n"
        "                       options:  array of {label, text} (4 options A–D)\n"
        "                       correct_label: string\n"
        "  story_hook       : string (markdown narrative wrapping the concept)\n"
        "  practice_problems: array of 3 objects, each with:\n"
        "                       problem: string\n"
        "                       hints:   array of strings (step-by-step, no answers)\n"
        "  teacher_alert    : string (plain text, 1 paragraph, gap summary + intervention)\n\n"
        "Respond ONLY with valid JSON, no markdown fences, no extra keys.\n"
        "Grade the content appropriately for a secondary-school student.\n"
        "Start micro-quiz questions from foundational sub-concepts, increasing in difficulty."
    )


def _build_user_message(topic_title: str, gap_index: float) -> str:
    return (
        f"Topic: {topic_title}\n"
        f"Gap Index (GI): {gap_index:.1f} out of 100 "
        f"(higher = more critical knowledge gap)\n\n"
        "Generate the complete remedial plan JSON for this student."
    )


async def generate_remedial_plan(
    db: AsyncSession,
    student_gap: StudentGap,
    *,
    requester_user_id: Optional[UUID] = None,
) -> Optional[dict]:
    """
    Call the LLM, validate the output, and persist it in ``student_gap.remedial_plan``.

    Parameters
    ----------
    db               : async SQLAlchemy session (must already have the gap row)
    student_gap      : the StudentGap ORM object to update
    requester_user_id: user ID used for AI token tracking (system/admin if None)

    Returns
    -------
    The validated remedial plan dict, or None on failure.
    """
    from app.services.ai import ai_chat_json

    if student_gap.gap_index <= GI_THRESHOLD:
        logger.debug(
            "[REMEDIAL] Skipping — GI=%.1f ≤ threshold=%.1f for student=%s topic=%s",
            student_gap.gap_index, GI_THRESHOLD,
            student_gap.student_id, student_gap.topic_id,
        )
        return None

    # Resolve topic title for the prompt
    topic_title = "Unknown Topic"
    topic = await db.get(Topic, student_gap.topic_id)
    if topic:
        topic_title = topic.title

    # Use student_id as a fallback token-tracking user when no explicit requester
    tracking_user_id = requester_user_id or student_gap.student_id

    system_prompt = _build_system_prompt()
    user_message = _build_user_message(topic_title, student_gap.gap_index)

    try:
        raw_plan = await ai_chat_json(
            db,
            tracking_user_id,
            system_prompt,
            user_message,
            max_tokens=REMEDIAL_MAX_TOKENS,
        )
    except Exception as exc:
        logger.error(
            "[REMEDIAL] LLM call failed for student=%s topic=%s: %s",
            student_gap.student_id, student_gap.topic_id, exc,
        )
        return None

    if "error" in raw_plan:
        logger.warning(
            "[REMEDIAL] LLM returned error payload for student=%s topic=%s: %s",
            student_gap.student_id, student_gap.topic_id, raw_plan,
        )
        return None

    # ── Pydantic validation ───────────────────────────────────
    try:
        validated = RemedialPlanSchema(**raw_plan)
    except ValidationError as exc:
        logger.warning(
            "[REMEDIAL] Pydantic validation failed for student=%s topic=%s: %s",
            student_gap.student_id, student_gap.topic_id, exc,
        )
        return None

    plan_dict = validated.model_dump()

    # ── Persist ───────────────────────────────────────────────
    student_gap.remedial_plan = plan_dict
    await db.flush()

    logger.info(
        "[REMEDIAL] Plan persisted for student=%s topic=%s GI=%.1f",
        student_gap.student_id, student_gap.topic_id, student_gap.gap_index,
    )
    return plan_dict


async def schedule_remedial_for_high_gi_gaps(
    db: AsyncSession,
    student_id: UUID,
    *,
    requester_user_id: Optional[UUID] = None,
) -> int:
    """
    Generate remedial plans for all high-GI gaps of a student that do not
    yet have a plan.  Intended to be called from a BackgroundTask.

    Returns the number of plans successfully generated.
    """
    result = await db.execute(
        select(StudentGap).where(
            and_(
                StudentGap.student_id == student_id,
                StudentGap.gap_index > GI_THRESHOLD,
                StudentGap.remedial_plan.is_(None),
            )
        )
    )
    gaps = result.scalars().all()

    generated = 0
    for gap in gaps:
        plan = await generate_remedial_plan(
            db, gap, requester_user_id=requester_user_id
        )
        if plan is not None:
            generated += 1

    if gaps:
        await db.commit()

    return generated
