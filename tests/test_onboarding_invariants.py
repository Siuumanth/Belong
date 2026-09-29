"""
Unit tests for Onboarding State Machine Invariants, Terminal Conditions,
Coverage Validation, and Extraction Rules.
"""

import pytest
from typing import Dict, Any, List
from unittest.mock import AsyncMock, patch

from onboarding.graph import (
    find_missing_high_priority_field,
    HIGH_PRIORITY_FIELDS,
    COVERAGE_MIN_CONFIDENCE,
    generate_response_node,
    extract_signals_node,
)
from onboarding.state import OnboardingState
from config import settings


# ---------------------------------------------------------------------------
# HIGH_PRIORITY_FIELDS spec checks
# ---------------------------------------------------------------------------

def test_high_priority_fields_behavioral_probe():
    """Ensures self.provides uses the concrete behavioral probe."""
    provides_spec = next((s for s in HIGH_PRIORITY_FIELDS if "self.provides" in s["keys"]), None)
    assert provides_spec is not None
    assert "naturally do for a partner" in provides_spec["prompt"].lower()
    assert "how do you support them" in provides_spec["prompt"].lower()


# ---------------------------------------------------------------------------
# find_missing_high_priority_field — basic coverage logic
# ---------------------------------------------------------------------------

def test_find_missing_high_priority_field_empty():
    """Identifies missing field when signals are empty."""
    signals: Dict[str, Any] = {}
    missing = find_missing_high_priority_field(signals, covered_areas=[])
    assert missing is not None
    assert missing["keys"][0] == "self.provides"


def test_find_missing_high_priority_field_duplicate_guard():
    """Prevents asking the same follow-up probe if already in covered_areas."""
    signals: Dict[str, Any] = {}
    covered_areas = ["probe:self.provides"]
    missing = find_missing_high_priority_field(signals, covered_areas=covered_areas)
    assert missing is not None
    assert missing["keys"][0] != "self.provides"
    assert missing["keys"][0] == "self.emotional_needs"


def test_find_missing_high_priority_field_all_covered():
    """Returns None when all high-priority fields have at least one confident signal."""
    signals = {
        "self.provides":          [{"label": "Listening",   "quote": "I listen patiently",  "confidence": 0.95}],
        "self.emotional_needs":   [{"label": "Reassurance", "quote": "clear reassurance",    "confidence": 0.90}],
        "self.conflict_style":    [{"label": "Calm",        "quote": "stay calm",            "confidence": 0.95}],
        "constraints.dealbreakers":[{"label": "Dishonesty", "quote": "dishonesty",           "confidence": 0.98}],
        "wants.partner_traits":   [{"label": "Active",      "quote": "active living",        "confidence": 0.90}],
    }
    missing = find_missing_high_priority_field(signals, covered_areas=[])
    assert missing is None


# ---------------------------------------------------------------------------
# Bug fix #2 — confidence-gated coverage (low-confidence signal must NOT count)
# ---------------------------------------------------------------------------

def test_coverage_requires_min_confidence():
    """A field with only low-confidence signals (< COVERAGE_MIN_CONFIDENCE) must still
    be considered missing, so that an adaptive probe is triggered for it.

    Regression: previously len(signals) > 0 was the only check, meaning an off-topic
    answer that produced a 0.51-confidence extraction would suppress further probing.
    """
    below_threshold = COVERAGE_MIN_CONFIDENCE - 0.01
    signals = {
        # self.provides has a signal but below the confidence floor — should still be flagged missing
        "self.provides": [{"label": "Something vague", "quote": "idk", "confidence": below_threshold}],
        # All others absent
    }
    missing = find_missing_high_priority_field(signals, covered_areas=[])
    assert missing is not None
    assert missing["keys"][0] == "self.provides", (
        f"Expected self.provides to be flagged missing due to low confidence "
        f"({below_threshold} < {COVERAGE_MIN_CONFIDENCE}), got: {missing['keys'][0]}"
    )


def test_coverage_passes_at_threshold():
    """A signal exactly at COVERAGE_MIN_CONFIDENCE must count as covering the field."""
    signals = {
        "self.provides":          [{"label": "Listening", "quote": "I listen", "confidence": COVERAGE_MIN_CONFIDENCE}],
        "self.emotional_needs":   [{"label": "Space",     "quote": "give me space", "confidence": 0.90}],
        "self.conflict_style":    [{"label": "Calm",      "quote": "stay calm",    "confidence": 0.95}],
        "constraints.dealbreakers":[{"label": "Lies",     "quote": "no lying",     "confidence": 0.99}],
        "wants.partner_traits":   [{"label": "Honest",    "quote": "be honest",    "confidence": 0.88}],
    }
    missing = find_missing_high_priority_field(signals, covered_areas=[])
    assert missing is None, f"All fields at/above threshold should be covered; got missing: {missing}"


def test_coverage_missing_when_signals_have_no_confidence_key():
    """Signals stored without a confidence key default to 0.0 and should NOT count as coverage."""
    signals = {
        # No confidence key — should default to 0.0, below threshold
        "self.provides": [{"label": "Something", "quote": "something"}],
    }
    missing = find_missing_high_priority_field(signals, covered_areas=[])
    assert missing is not None
    assert missing["keys"][0] == "self.provides"


# ---------------------------------------------------------------------------
# Bug fix #1 — off-topic probe answer must not loop; hard cap must complete
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_follow_up_hard_cap_invariant():
    """Ensures that when follow_up_count reaches MAX_FOLLOW_UPS, state immediately completes
    even when signals are entirely empty."""
    max_fups = settings.MAX_FOLLOW_UPS  # 2
    state: OnboardingState = {
        "conversation_id": "test-conv",
        "user_id": "test-user",
        "current_area_index": len(settings.ONBOARDING_QUESTIONS),  # core questions done
        "follow_up_count": max_fups,  # already at cap
        "covered_areas": ["q1", "q2", "q3", "q4", "q5", "q6"],
        "extracted_signals": {},  # no signals — must still terminate
        "latest_user_input": "I value communication and empathy.",
        "status": "active",
    }

    with patch("onboarding.graph.finalize_profile", new_callable=AsyncMock) as mock_finalize, \
         patch("onboarding.graph.get_llm") as mock_llm:
        mock_client = AsyncMock()
        mock_client.ainvoke.return_value = "Thank you! Profile completed."
        mock_llm.return_value = mock_client

        res = await generate_response_node(state)
        assert res["status"] == "completed"
        assert res["follow_up_count"] <= max_fups
        mock_finalize.assert_called_once()


@pytest.mark.asyncio
async def test_off_topic_probe_answer_still_completes():
    """Simulates Alice's bug: user answers a probe with completely off-topic content.
    The off-topic answer produces only low-confidence signals for the probed field,
    but after MAX_FOLLOW_UPS the conversation must complete — not loop.

    Previously this caused an infinite loop because:
    1. _active_probe was re-introduced by a double assignment in extract_signals_node.
    2. Low-confidence off-topic signals weren't suppressing the re-probe guard,
       so the system attempted a third probe and hit an AssertionError, leaving
       status='active' permanently in the database.
    """
    max_fups = settings.MAX_FOLLOW_UPS  # 2

    # After 6 core questions + 1 probe (for self.provides), simulate probe answer turn
    # with follow_up_count already at 1 and _active_probe still in extracted_signals (as
    # it would be when loaded from DB).
    state_before_probe_answer: OnboardingState = {
        "conversation_id": "test-alice",
        "user_id": "test-user",
        "current_area_index": len(settings.ONBOARDING_QUESTIONS),  # 6
        "follow_up_count": 1,
        "covered_areas": [
            "q1_intent_partner", "q2_emotional_needs", "q3_conflict_provides",
            "q4_lifestyle_values", "q5_personality", "q6_dealbreakers",
            "probe:self.provides",
        ],
        # _active_probe carried via extracted_signals (as persisted in DB)
        "extracted_signals": {
            "_active_probe": {"field": "self.provides", "prompt": "What do you naturally do for a partner?"},
            # self.provides is still empty (probe answer was off-topic)
            "constraints.dealbreakers": [
                {"label": "No smoking", "quote": "smoking is a hard no", "confidence": 0.99}
            ],
        },
        "latest_user_input": "smoking is a hard no, I have asthma. also dishonesty in any form.",
        "status": "active",
    }

    with patch("onboarding.graph.finalize_profile", new_callable=AsyncMock) as mock_finalize, \
         patch("onboarding.graph.get_llm") as mock_llm:
        mock_client = AsyncMock()
        mock_client.ainvoke.return_value = "Assistant response."
        mock_llm.return_value = mock_client

        # Step 1: extraction node cleans _active_probe, extracts from off-topic answer
        extract_result = await extract_signals_node(state_before_probe_answer)

        # _active_probe must NOT be in the returned signals
        assert "_active_probe" not in extract_result["extracted_signals"], \
            "_active_probe leaked into persisted signals"

        # Merge extraction result into state (as LangGraph would)
        merged_state = {**state_before_probe_answer, **extract_result}

        # Step 2: generate_response uses the merged (clean) state
        gen_result = await generate_response_node(merged_state)

        # With follow_up_count=1 after the off-topic answer, the system can fire one more probe
        # (follow_up_count→2) OR complete if already at cap.
        # Either way it must NEVER exceed MAX_FOLLOW_UPS and must eventually complete.
        assert gen_result["follow_up_count"] <= max_fups, \
            f"follow_up_count {gen_result['follow_up_count']} exceeded cap {max_fups}"

        # Simulate the second probe answer (also off-topic — worst case)
        if gen_result["status"] == "active":
            state2: OnboardingState = {
                **merged_state,
                **gen_result,
                "latest_user_input": "smoking is a hard no, dishonesty is a dealbreaker",
            }
            extract_result2 = await extract_signals_node(state2)
            merged_state2 = {**state2, **extract_result2}
            gen_result2 = await generate_response_node(merged_state2)

            # Now at MAX_FOLLOW_UPS — must be completed
            assert gen_result2["status"] == "completed", \
                f"Expected 'completed' after {max_fups} follow-ups with off-topic answers; got '{gen_result2['status']}'"
            assert gen_result2["follow_up_count"] <= max_fups
            mock_finalize.assert_called()
        else:
            # Already completed after first probe — also valid
            assert gen_result["status"] == "completed"
            mock_finalize.assert_called()


# ---------------------------------------------------------------------------
# Hard turn-count invariant
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_max_total_answers_never_exceeds_8():
    """
    Simulates a worst-case user who gives answers triggering probes.
    Asserts that total user turns never exceeds 6 core + 2 follow-ups = 8.
    Never reaches Q9 or Q10.
    """
    max_fups = settings.MAX_FOLLOW_UPS
    assert max_fups == 2
    num_core = len(settings.ONBOARDING_QUESTIONS)
    assert num_core == 6

    current_area_index = 0
    follow_up_count = 0
    covered_areas: List[str] = []
    extracted_signals: Dict[str, Any] = {}
    status = "active"
    turns = 0

    with patch("onboarding.graph.finalize_profile", new_callable=AsyncMock), \
         patch("onboarding.graph.get_llm") as mock_llm:
        mock_client = AsyncMock()
        mock_client.ainvoke.return_value = "Assistant response."
        mock_llm.return_value = mock_client

        while status == "active" and turns < 15:
            turns += 1
            state: OnboardingState = {
                "conversation_id": "test-conv",
                "user_id": "test-user",
                "current_area_index": current_area_index,
                "follow_up_count": follow_up_count,
                "covered_areas": covered_areas,
                "extracted_signals": extracted_signals,
                "latest_user_input": "Generic response",
                "status": status,
            }

            res = await generate_response_node(state)
            current_area_index = res["current_area_index"]
            follow_up_count = res["follow_up_count"]
            covered_areas = res["covered_areas"]
            status = res["status"]

            assert follow_up_count <= max_fups, f"follow_up_count exceeded limit on turn {turns}"

    assert status == "completed", "Conversation failed to complete"
    assert turns <= 8, f"Conversation took {turns} turns — must never exceed 8 (6 core + 2 follow-ups)."
