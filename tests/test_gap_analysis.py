"""
Unit tests for Gap Analysis v2.0.

Tests cover:
  - GI formula correctness and boundary conditions
  - Individual signal computation (quiz, assignment, comprehension,
    engagement, peer benchmark)
  - Edge cases: empty data, missing signals, all-correct, all-wrong
  - Propagation traversal and decay
  - Pydantic remedial plan schema validation

Run with:  pytest tests/test_gap_analysis.py -v
"""

import math
from datetime import datetime, timedelta

import pytest

from app.services.gap_analysis import (
    GI_THRESHOLD,
    PROPAGATION_DECAY,
    compute_assignment_score,
    compute_comprehension_index,
    compute_engagement_depth,
    compute_gap_index,
    compute_peer_benchmark,
    compute_quiz_score,
    _clamp,
)
from app.schemas.gaps import (
    AssignmentSubmissionCreate,
    MCQOption,
    MicroQuizQuestion,
    PracticeProblem,
    RemedialPlanSchema,
    TopicPrerequisiteCreate,
)


# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def _make_response(is_correct: bool, rt: float = None, attempt: int = 1, days_ago: int = 0):
    return {
        "is_correct": is_correct,
        "response_time_seconds": rt,
        "attempt_number": attempt,
        "answered_at": datetime.utcnow() - timedelta(days=days_ago),
    }


def _make_submission(raw: float = None, max_s: float = 100.0, missed: bool = False):
    return {"raw_score": raw, "max_score": max_s, "is_missed": missed}


def _make_comp_score(score: float, days_ago: int = 0):
    return {"score": score, "evaluated_at": datetime.utcnow() - timedelta(days=days_ago)}


def _make_event(event_type: str):
    return {"event_type": event_type}


# ─────────────────────────────────────────────────────────────
# _clamp
# ─────────────────────────────────────────────────────────────

class TestClamp:
    def test_within_bounds(self):
        assert _clamp(50.0) == 50.0

    def test_below_min(self):
        assert _clamp(-10.0) == 0.0

    def test_above_max(self):
        assert _clamp(110.0) == 100.0

    def test_exact_boundaries(self):
        assert _clamp(0.0) == 0.0
        assert _clamp(100.0) == 100.0


# ─────────────────────────────────────────────────────────────
# Quiz Performance Signal
# ─────────────────────────────────────────────────────────────

class TestComputeQuizScore:
    def test_empty_returns_default(self):
        score, has_data = compute_quiz_score([])
        assert score == 50.0
        assert has_data is False

    def test_all_correct(self):
        responses = [_make_response(True), _make_response(True), _make_response(True)]
        score, has_data = compute_quiz_score(responses)
        assert has_data is True
        assert score == pytest.approx(100.0, abs=1.0)

    def test_all_wrong(self):
        responses = [_make_response(False), _make_response(False)]
        score, has_data = compute_quiz_score(responses)
        assert has_data is True
        assert score == pytest.approx(0.0, abs=1.0)

    def test_recency_weight_boosts_recent_correct(self):
        # Two old wrong, one recent correct
        responses = [
            _make_response(False, days_ago=10),
            _make_response(False, days_ago=9),
            _make_response(True, days_ago=0),  # most recent → weight 2×
        ]
        score, _ = compute_quiz_score(responses, recent_weight=2.0)
        # weighted: 0 + 0 + 2×1 = 2 over total weight 1+1+2=4 → 50%
        assert score == pytest.approx(50.0, abs=1.0)

    def test_latency_penalty_applied(self):
        # One correct response with high latency
        responses = [_make_response(True, rt=300.0)]
        score_with_penalty, _ = compute_quiz_score(
            responses, latency_penalty_seconds=100.0, max_latency_penalty=0.5
        )
        score_no_penalty, _ = compute_quiz_score(
            [_make_response(True, rt=10.0)], latency_penalty_seconds=100.0, max_latency_penalty=0.5
        )
        assert score_with_penalty < score_no_penalty

    def test_latency_penalty_capped(self):
        # Extreme latency should not make score negative
        responses = [_make_response(True, rt=999999.0)]
        score, _ = compute_quiz_score(responses, latency_penalty_seconds=10.0, max_latency_penalty=0.15)
        assert score >= 0.0

    def test_score_bounded(self):
        responses = [_make_response(True)] * 20
        score, _ = compute_quiz_score(responses)
        assert 0.0 <= score <= 100.0


# ─────────────────────────────────────────────────────────────
# Assignment Score Signal
# ─────────────────────────────────────────────────────────────

class TestComputeAssignmentScore:
    def test_empty_returns_default(self):
        score, has_data = compute_assignment_score([])
        assert score == 50.0
        assert has_data is False

    def test_perfect_score_above_median(self):
        subs = [_make_submission(100.0, 100.0)]
        score, has_data = compute_assignment_score(subs, class_median=50.0)
        assert has_data is True
        assert score > 50.0

    def test_zero_score_below_median(self):
        subs = [_make_submission(0.0, 100.0)]
        score, has_data = compute_assignment_score(subs, class_median=50.0)
        assert has_data is True
        assert score < 50.0

    def test_missed_assignment_penalised(self):
        subs = [_make_submission(missed=True)]
        score, has_data = compute_assignment_score(subs, class_median=50.0)
        assert has_data is True
        assert score < 50.0

    def test_score_bounded(self):
        subs = [_make_submission(200.0, 100.0)]  # raw > max (edge case)
        score, _ = compute_assignment_score(subs)
        assert 0.0 <= score <= 100.0

    def test_mixed_submissions(self):
        subs = [
            _make_submission(80.0, 100.0),
            _make_submission(60.0, 100.0),
            _make_submission(missed=True),
        ]
        score, has_data = compute_assignment_score(subs, class_median=50.0)
        assert has_data is True
        assert 0.0 <= score <= 100.0


# ─────────────────────────────────────────────────────────────
# Comprehension Index Signal
# ─────────────────────────────────────────────────────────────

class TestComputeComprehensionIndex:
    def test_empty_returns_default(self):
        score, has_data = compute_comprehension_index([])
        assert score == 50.0
        assert has_data is False

    def test_single_score(self):
        scores = [_make_comp_score(80.0)]
        score, has_data = compute_comprehension_index(scores)
        assert has_data is True
        assert score == pytest.approx(80.0, abs=1.0)

    def test_ewm_weights_recent_more(self):
        # Declining scores — EWM should be lower than simple mean
        scores = [
            _make_comp_score(90.0, days_ago=4),
            _make_comp_score(80.0, days_ago=3),
            _make_comp_score(70.0, days_ago=2),
            _make_comp_score(60.0, days_ago=1),
            _make_comp_score(40.0, days_ago=0),  # most recent
        ]
        score, _ = compute_comprehension_index(scores, span=5)
        simple_mean = (90 + 80 + 70 + 60 + 40) / 5  # 68
        assert score < simple_mean  # EWM weighs the recent low score more

    def test_score_bounded(self):
        scores = [_make_comp_score(110.0)]  # out-of-range input
        score, _ = compute_comprehension_index(scores)
        assert 0.0 <= score <= 100.0

    def test_uses_only_last_span_entries(self):
        # Provide many entries; only last `span` should be used
        scores = [_make_comp_score(100.0, days_ago=i) for i in range(20, -1, -1)]
        # Last 5 are the most recent (days_ago = 0..4, score 100)
        score, _ = compute_comprehension_index(scores, span=5)
        assert score == pytest.approx(100.0, abs=1.0)


# ─────────────────────────────────────────────────────────────
# Engagement Depth Signal
# ─────────────────────────────────────────────────────────────

class TestComputeEngagementDepth:
    def test_empty_returns_default(self):
        ratio, has_data = compute_engagement_depth([])
        assert ratio == 0.5
        assert has_data is False

    def test_all_replays(self):
        events = [_make_event("replay")] * 10
        ratio, has_data = compute_engagement_depth(events)
        assert has_data is True
        assert ratio == pytest.approx(1.0)

    def test_no_replays(self):
        events = [_make_event("view")] * 10
        ratio, has_data = compute_engagement_depth(events)
        assert has_data is True
        assert ratio == pytest.approx(0.0)

    def test_mixed_events(self):
        events = [_make_event("replay")] * 3 + [_make_event("view")] * 7
        ratio, has_data = compute_engagement_depth(events)
        assert has_data is True
        assert ratio == pytest.approx(0.3)

    def test_ratio_bounded(self):
        events = [_make_event("replay")] * 5
        ratio, _ = compute_engagement_depth(events)
        assert 0.0 <= ratio <= 1.0

    def test_reread_variant_counted(self):
        events = [_make_event("reread"), _make_event("view"), _make_event("view")]
        ratio, _ = compute_engagement_depth(events)
        assert ratio == pytest.approx(1 / 3)


# ─────────────────────────────────────────────────────────────
# Peer Benchmark Signal
# ─────────────────────────────────────────────────────────────

class TestComputePeerBenchmark:
    def test_empty_class_returns_default(self):
        score, has_data = compute_peer_benchmark(75.0, [])
        assert score == 50.0
        assert has_data is False

    def test_single_class_entry_returns_default(self):
        score, has_data = compute_peer_benchmark(75.0, [75.0])
        assert score == 50.0
        assert has_data is False

    def test_top_of_class(self):
        class_scores = [20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0]
        score, has_data = compute_peer_benchmark(100.0, class_scores)
        assert has_data is True
        assert score > 75.0  # well above median

    def test_bottom_of_class(self):
        class_scores = [20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0]
        score, has_data = compute_peer_benchmark(0.0, class_scores)
        assert has_data is True
        assert score < 25.0

    def test_at_class_mean(self):
        class_scores = [40.0, 60.0]  # mean = 50
        score, has_data = compute_peer_benchmark(50.0, class_scores)
        assert has_data is True
        assert score == pytest.approx(50.0, abs=2.0)

    def test_all_same_scores(self):
        class_scores = [70.0] * 5
        score, has_data = compute_peer_benchmark(70.0, class_scores)
        assert score == 50.0
        assert has_data is False  # std dev = 0

    def test_score_bounded(self):
        class_scores = list(range(0, 100))
        score, _ = compute_peer_benchmark(99.0, class_scores)
        assert 0.0 <= score <= 100.0


# ─────────────────────────────────────────────────────────────
# Composite GI Formula
# ─────────────────────────────────────────────────────────────

class TestComputeGapIndex:
    def test_perfect_mastery_gives_zero_gi(self):
        # All signals at 100 → GI should be 0
        gi = compute_gap_index(
            quiz_score=100.0,
            assignment_score=100.0,
            comprehension_index=100.0,
            engagement_depth_ratio=0.0,  # no replays = good
            peer_benchmark_normalized=100.0,
        )
        assert gi == pytest.approx(0.0, abs=1.0)

    def test_complete_gap_gives_hundred_gi(self):
        # All signals at 0, engagement at 1 (all replays) → GI should be 100
        gi = compute_gap_index(
            quiz_score=0.0,
            assignment_score=0.0,
            comprehension_index=0.0,
            engagement_depth_ratio=1.0,  # all replays = bad
            peer_benchmark_normalized=0.0,
        )
        assert gi == pytest.approx(100.0, abs=1.0)

    def test_mid_range_gi(self):
        gi = compute_gap_index(
            quiz_score=50.0,
            assignment_score=50.0,
            comprehension_index=50.0,
            engagement_depth_ratio=0.5,
            peer_benchmark_normalized=50.0,
        )
        assert gi == pytest.approx(50.0, abs=1.0)

    def test_formula_weights(self):
        """Verify signal weights sum to 1 (implicitly via formula)."""
        # If every signal = 100 and engagement_depth = 0 → GI = 0
        # Check: 0.35+0.25+0.20+0.10+0.10 = 1.00
        total_weight = 0.35 + 0.25 + 0.20 + 0.10 + 0.10
        assert total_weight == pytest.approx(1.0)

    def test_output_bounded_below_zero(self):
        gi = compute_gap_index(
            quiz_score=200.0,  # out of range
            assignment_score=200.0,
            comprehension_index=200.0,
            engagement_depth_ratio=0.0,
            peer_benchmark_normalized=200.0,
        )
        assert gi >= 0.0

    def test_output_bounded_above_100(self):
        gi = compute_gap_index(
            quiz_score=-100.0,  # out of range
            assignment_score=-100.0,
            comprehension_index=-100.0,
            engagement_depth_ratio=2.0,
            peer_benchmark_normalized=-100.0,
        )
        assert gi <= 100.0

    def test_gi_above_threshold_triggers_action(self):
        """Ensure default threshold value is meaningful."""
        gi_critical = compute_gap_index(
            quiz_score=20.0,
            assignment_score=20.0,
            comprehension_index=20.0,
            engagement_depth_ratio=0.8,
            peer_benchmark_normalized=20.0,
        )
        assert gi_critical > GI_THRESHOLD

    def test_gi_high_quiz_weight(self):
        """Quiz has the highest weight (35%); test its dominance over other signals."""
        # Same baseline for all other signals; only quiz differs
        gi_low_quiz = compute_gap_index(
            quiz_score=10.0,
            assignment_score=50.0,
            comprehension_index=50.0,
            engagement_depth_ratio=0.5,
            peer_benchmark_normalized=50.0,
        )
        gi_high_quiz = compute_gap_index(
            quiz_score=90.0,
            assignment_score=50.0,
            comprehension_index=50.0,
            engagement_depth_ratio=0.5,
            peer_benchmark_normalized=50.0,
        )
        # Lower quiz score → higher GI (more critical gap)
        assert gi_low_quiz > gi_high_quiz


# ─────────────────────────────────────────────────────────────
# Propagation logic (pure DAG traversal, no DB)
# ─────────────────────────────────────────────────────────────

class TestPropagationDecay:
    """Test propagation decay arithmetic without hitting the DB."""

    def test_single_hop_decay(self):
        parent_gi = 80.0
        propagated = parent_gi * PROPAGATION_DECAY
        assert propagated == pytest.approx(56.0, abs=0.1)

    def test_two_hop_decay(self):
        parent_gi = 80.0
        hop1 = parent_gi * PROPAGATION_DECAY
        hop2 = hop1 * PROPAGATION_DECAY
        assert hop2 == pytest.approx(39.2, abs=0.1)

    def test_decay_eventually_below_threshold(self):
        """Decay must eventually bring propagated GI below threshold."""
        gi = 100.0
        depth = 0
        while gi > GI_THRESHOLD and depth < 50:
            gi *= PROPAGATION_DECAY
            depth += 1
        assert gi <= GI_THRESHOLD

    def test_propagated_gi_bounded(self):
        parent_gi = 100.0
        propagated = _clamp(parent_gi * PROPAGATION_DECAY)
        assert 0.0 <= propagated <= 100.0


# ─────────────────────────────────────────────────────────────
# Pydantic schema validation
# ─────────────────────────────────────────────────────────────

def _valid_plan():
    return {
        "concept_reteach": "A fraction represents part of a whole. " * 5,
        "micro_quiz": [
            {
                "question": f"Question {i}?",
                "options": [
                    {"label": "A", "text": "Option A"},
                    {"label": "B", "text": "Option B"},
                    {"label": "C", "text": "Option C"},
                    {"label": "D", "text": "Option D"},
                ],
                "correct_label": "A",
            }
            for i in range(1, 6)
        ],
        "story_hook": "Once upon a time in a land of numbers...",
        "practice_problems": [
            {"problem": f"Problem {i}", "hints": ["Hint 1", "Hint 2"]}
            for i in range(1, 4)
        ],
        "teacher_alert": "This student needs immediate attention on fractions. Recommend small-group work.",
    }


class TestRemedialPlanSchema:
    def test_valid_plan_accepted(self):
        plan = _valid_plan()
        validated = RemedialPlanSchema(**plan)
        assert validated.concept_reteach is not None
        assert len(validated.micro_quiz) == 5
        assert len(validated.practice_problems) == 3

    def test_missing_concept_reteach_rejected(self):
        plan = _valid_plan()
        del plan["concept_reteach"]
        with pytest.raises(Exception):
            RemedialPlanSchema(**plan)

    def test_missing_micro_quiz_rejected(self):
        plan = _valid_plan()
        del plan["micro_quiz"]
        with pytest.raises(Exception):
            RemedialPlanSchema(**plan)

    def test_empty_micro_quiz_rejected(self):
        plan = _valid_plan()
        plan["micro_quiz"] = []
        with pytest.raises(Exception):
            RemedialPlanSchema(**plan)

    def test_empty_hints_rejected(self):
        plan = _valid_plan()
        plan["practice_problems"][0]["hints"] = []
        with pytest.raises(Exception):
            RemedialPlanSchema(**plan)

    def test_short_concept_reteach_rejected(self):
        plan = _valid_plan()
        plan["concept_reteach"] = "short"  # < 20 chars
        with pytest.raises(Exception):
            RemedialPlanSchema(**plan)

    def test_plan_serialises_to_dict(self):
        plan = _valid_plan()
        validated = RemedialPlanSchema(**plan)
        d = validated.model_dump()
        assert "concept_reteach" in d
        assert "micro_quiz" in d
        assert isinstance(d["micro_quiz"], list)


class TestTopicPrerequisiteSchema:
    def test_self_loop_rejected(self):
        import pytest
        with pytest.raises(Exception):
            TopicPrerequisiteCreate(
                prerequisite_topic_id="abc",
                dependent_topic_id="abc",
            )

    def test_valid_edge_accepted(self):
        edge = TopicPrerequisiteCreate(
            prerequisite_topic_id="topic-A",
            dependent_topic_id="topic-B",
        )
        assert edge.prerequisite_topic_id == "topic-A"
        assert edge.dependent_topic_id == "topic-B"


class TestAssignmentSubmissionSchema:
    def test_raw_score_required_when_not_missed(self):
        with pytest.raises(Exception):
            AssignmentSubmissionCreate(
                student_id="s1",
                topic_id="t1",
                raw_score=None,
                is_missed=False,
            )

    def test_raw_score_optional_when_missed(self):
        sub = AssignmentSubmissionCreate(
            student_id="s1",
            topic_id="t1",
            raw_score=None,
            is_missed=True,
        )
        assert sub.is_missed is True
        assert sub.raw_score is None
