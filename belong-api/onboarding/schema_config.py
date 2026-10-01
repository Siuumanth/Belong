"""
Centralized Profile Dimensions Schema
=====================================
Defines the authoritative vocabulary of supported profile taxonomy dimensions.
Used by the signal extraction engine to map raw user answers into structured profile sections.
"""

PROFILE_DIMENSIONS = {
    "self": [
        "values",
        "lifestyle",
        "personality_signals",
        "interests",
        "life_goals",
        "conflict_style",
        "provides",
        "emotional_needs",
    ],
    "wants": [
        "partner_traits",
        "partner_values",
        "emotional_needs",
        "relationship_expectations",
        "desired_lifestyle",
    ],
    "constraints": [
        "dealbreakers",
    ],
}
