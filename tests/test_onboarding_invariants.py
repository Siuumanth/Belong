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
    generate_response_node,
    extract_signals_node
)
from onboarding.state import OnboardingState
from config import settings


def test_high_priority_fields_behavioral_probe():
    """Ensures self.provides uses the concrete behavioral probe."""
    provides_spec = next((s for s in HIGH_PRIORITY_FIELDS if "self.provides" in s["keys"]), None)
    assert provides_spec is not None
    assert "naturally do for a partner" in provides_spec["prompt"].lower()
    assert "how do you support them" in provides_spec["prompt"].lower()


def test_find_missing_high_priority_field_empty():
    """Identifies missing field when signals are empty."""
    signals: Dict[str, Any] = {}
    missing = find_missing_high_priority_field(signals, covered_areas=[])
    assert missing is not None
    assert missing["keys"][0] == "self.provides"


def test_find_missing_high_priority_field_duplicate_guard():
    """Prevents asking the same follow-up probe if already in covered_areas."""
    signals: Dict[str, Any] = {}
    # Mark self.provides probe as already asked
    covered_areas = ["probe:self.provides"]
    missing = find_missing_high_priority_field(signals, covered_areas=covered_areas)
    assert missing is not None
    # Must NOT re-ask self.provides
    assert missing["keys"][0] != "self.provides"
    # Should move to next missing field
    assert missing["keys"][0] == "self.emotional_needs"


def test_find_missing_high_priority_field_all_covered():
    """Returns None when all high-priority fields have at least one signal."""
    signals = {
        "self.provides": [{"label": "Listening", "quote": "I listen patiently"}],
        "self.emotional_needs": [{"label": "Reassurance", "quote": "clear reassurance"}],
        "self.conflict_style": [{"label": "Calm", "quote": "stay calm"}],
        "constraints.dealbreakers": [{"label": "Dishonesty", "quote": "dishonesty"}],
        "wants.partner_traits": [{"label": "Active", "quote": "active living"}],
    }
    missing = find_missing_high_priority_field(signals, covered_areas=[])
    assert missing is None


@pytest.mark.asyncio
async def test_follow_up_hard_cap_invariant():
    """Ensures that when follow_up_count reaches MAX_FOLLOW_UPS, state immediately completes."""
    max_fups = settings.MAX_FOLLOW_UPS  # 2
    state: OnboardingState = {
        "conversation_id": "test-conv",
        "user_id": "test-user",
        "current_area_index": len(settings.ONBOARDING_QUESTIONS),  # Core questions done
        "follow_up_count": max_fups,  # Already at cap
        "covered_areas": ["q1", "q2", "q3", "q4", "q5", "q6"],
        "extracted_signals": {},  # Even with missing signals, must terminate!
        "latest_user_input": "I value communication and empathy.",
        "status": "active"
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

    # Track conversation progression across turns
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
                "status": status
            }

            res = await generate_response_node(state)
            current_area_index = res["current_area_index"]
            follow_up_count = res["follow_up_count"]
            covered_areas = res["covered_areas"]
            status = res["status"]

            # Invariant on every single turn
            assert follow_up_count <= max_fups, f"follow_up_count exceeded limit on turn {turns}"

    assert status == "completed", "Conversation failed to complete"
    # Core (6) + Follow-ups (at most 2) = max 8 turns
    assert turns <= 8, f"Conversation took {turns} turns! Must never exceed 8 turns (never Q9/Q10)."
