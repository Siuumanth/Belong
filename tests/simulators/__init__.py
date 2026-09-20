"""
User Simulator Package
======================
Provides configurable simulated user actors (UserSimulator) and persona builders (PersonaConfig)
for end-to-end multi-turn onboarding, embedding extraction, and persona matching tests.
"""

from .user_simulator import UserSimulator, PersonaConfig

__all__ = ["UserSimulator", "PersonaConfig"]
