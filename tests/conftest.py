import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List
import pytest

# Add belong-api and belong-workers to sys.path for cross-module testing
ROOT_DIR = Path(__file__).parent.parent
BELONG_API_DIR = ROOT_DIR / "belong-api"
BELONG_WORKERS_DIR = ROOT_DIR / "belong-workers"

sys.path.insert(0, str(BELONG_WORKERS_DIR))
sys.path.insert(0, str(BELONG_API_DIR))
sys.path.insert(0, str(ROOT_DIR))

FIXTURES_DIR = Path(__file__).parent / "fixtures"

@pytest.fixture(scope="session")
def golden_personas() -> List[Dict[str, Any]]:
    """Fixture providing loaded personas from personas.json."""
    personas_path = FIXTURES_DIR / "personas.json"
    with open(personas_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("personas", [])

@pytest.fixture(scope="session")
def expected_outcomes() -> Dict[str, Any]:
    """Fixture providing expected pair outcome invariants from expected_outcomes.json."""
    outcomes_path = FIXTURES_DIR / "expected_outcomes.json"
    with open(outcomes_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("outcomes", {})

@pytest.fixture(scope="session")
def personas_map(golden_personas: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Map of persona_id -> persona dict."""
    return {p["id"]: p for p in golden_personas}

