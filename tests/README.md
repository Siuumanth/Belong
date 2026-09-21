# Belong User Simulation & Automated Testing Guide

This directory contains the **User Simulation Test Framework** for the Belong compatibility matching platform. Instead of testing isolated code functions, the test suite simulates **actual user journeys and user actors (`UserSimulator`)** throughout their lifecycle: demographic registration, multi-turn AI onboarding conversations, trait extraction, vector embeddings, and qualitative matching.

---

## 📁 Directory Structure

```
tests/
├── README.md                              # This guide
├── pytest.ini                             # Pytest configuration & markers
├── conftest.py                            # Pytest session fixtures & persona loaders
├── run_onboarding_simulation.py           # CLI runner for live onboarding simulation
├── fixtures/
│   ├── personas.json                      # Golden synthetic user personas (Alice, Bob, etc.)
│   └── expected_outcomes.json             # Ground-truth compatibility & filter outcome invariants
├── simulators/
│   ├── __init__.py                        # Package exports (UserSimulator, PersonaConfig)
│   └── user_simulator.py                  # User actor engine & configurable persona builder
└── simulations/
    ├── __init__.py
    ├── test_user_configurable_personas.py # Unit & configuration tests for dynamic personas
    ├── test_user_onboarding_simulation.py # Multi-turn AI onboarding dialogue simulation tests
    └── test_user_ecosystem_simulation.py  # Community ecosystem matching & invariant tests
```

---

## 🛠️ User Configurability Guide (`PersonaConfig` & `PersonaBuilder`)

You can create or customize test users programmatically or by extending `fixtures/personas.json`.

### Option 1: Fluid Builder (`PersonaConfig.builder`)

Use `PersonaConfig.builder(id)` to construct fully customized test users:

```python
from simulators.user_simulator import PersonaConfig, UserSimulator

# Build a custom user persona
my_custom_persona = (
    PersonaConfig.builder("user_sam_nyc")
    .with_category("custom_test")
    .with_age(29, preferred_min=25, preferred_max=35)
    .with_gender("male", preferred_genders=["female"])
    .with_location(latitude=40.7128, longitude=-74.0060, max_distance_km=30) # NYC
    .with_relationship_goal("long-term", required_goal="long-term")
    .with_responses(
        q1_intent_partner="I am seeking a partner who values deep communication and growth.",
        q2_emotional_needs="I need active listening and calm reassurance during stress.",
        q3_conflict_provides="I express my feelings calmly and resolve issues collaboratively.",
        q4_lifestyle_values="Product design, morning yoga, plant-based cooking, and hiking.",
        q5_personality="Friends describe me as warm, thoughtful, empathetic, and grounded.",
        q6_dealbreakers="Smoking of any kind is an absolute non-negotiable dealbreaker."
    )
    .build()
)

# Instantiate a user simulator actor
user_sam = UserSimulator(my_custom_persona)
```

### Option 2: Pre-defined Golden Personas (`fixtures/personas.json`)

You can also load standard synthetic personas directly:

```python
persona_dict = personas_map["cp_alice"]
persona = PersonaConfig.from_dict(persona_dict)
user_alice = UserSimulator(persona)
```

---

## 🚀 How to Run Each Test

### 1. Configurable Persona Tests
Tests user configuration capabilities, default fallbacks, payload generation, and batch population creation.

- **What it tests**: Validates that customized demographics, coordinates, dealbreakers, and multi-turn responses correctly populate API payloads.
- **Command**:
  ```bash
  pytest tests/simulations/test_user_configurable_personas.py -v
  ```

---

### 2. User Onboarding Dialogue Simulation Tests
Simulates realistic users going through interactive, multi-turn AI onboarding conversations.

- **What it tests**:
  - `POST /onboarding/session` session initialization.
  - Multi-turn `POST /onboarding/message` user response turns (`q1` through `q6`).
  - LangGraph onboarding graph state transitions (`active` -> `completed`).
- **Command**:
  ```bash
  pytest tests/simulations/test_user_onboarding_simulation.py -v
  ```

---

### 3. User Ecosystem & Matching Simulation Tests
Simulates a population of diverse users (Alice, Bob, Elena, Felix, Ian, Julia, Eve, Frank, Quinn, Ryan) interacting simultaneously.

- **What it tests**:
  - **Complementary Match**: Alice & Bob match with `strong_alignment`.
  - **Dealbreaker Exclusion**: Eve (non-smoker) vs Frank (smoker) triggers dealbreaker violation.
  - **Conflict Style Clash**: Ian (anxious pursuer) vs Julia (stonewaller) flags conflict clash.
  - **Geographic Distance Boundary**: Quinn (Seattle) vs Ryan (SF) excluded by distance filters.
- **Command**:
  ```bash
  pytest tests/simulations/test_user_ecosystem_simulation.py -v
  ```

---

### 4. Run All User Simulation Tests
Runs all simulation test suites using the `simulation` pytest marker.

- **Command**:
  ```bash
  pytest -m simulation -v
  ```

---

### 5. Live Microservice End-to-End Test (`test_e2e_integration.py`)
Tests full async worker pipeline (FastAPI + PostgreSQL pgvector + RabbitMQ + Workers).

- **Requires**: Local services running (`docker compose up -d` or `belong-api` running on port 8000).
- **Command**:
  ```bash
  pytest tests/test_e2e_integration.py -m e2e -v
  ```

---

### 6. Interactive CLI Simulation Runner (`run_onboarding_simulation.py`)
CLI script that runs full multi-turn onboarding dialogues for all synthetic personas in `personas.json` against a live API service.

- **Requires**: `belong-api` running on port 8000.
- **Command**:
  ```bash
  python tests/run_onboarding_simulation.py
  ```

---

## 🔒 Gateway Authentication Bypass (`DISABLE_AUTH=true`)

When testing through the **API Gateway** (port `9000`), JWT authentication can be temporarily bypassed by setting `DISABLE_AUTH=true`.

1. **Enable in `.env` or Environment**:
   ```env
   DISABLE_AUTH=true
   ```
2. **Gateway Behavior with `DISABLE_AUTH=true`**:
   - Skips JWT token signature verification.
   - Allows unauthenticated calls to protected `/profiles`, `/onboarding`, and `/matches` routes.
   - Preserves client-supplied `X-User-ID` headers so `UserSimulator` actors can simulate specific user IDs through the Gateway.
3. **Run Simulation Tests through Gateway**:
   ```bash
   BELONG_API_URL=http://localhost:9000 pytest -m simulation -v
   ```

