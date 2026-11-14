# 07. Testing, Synthetic Evaluation & Simulation Harness

> **How to Test & Validate an AI Matchmaking Engine Without Human Labelers**  
> *Persona simulators, behavioral invariant testing, Stage 1 recall benchmarking, and regression defense.*

---

## 1. The Core Challenge: Why Testing AI Systems is Hard

In traditional software, testing is deterministic:
$$\text{assert } f(x) == y$$
In AI-driven systems like Belong, traditional unit tests fail because:
1. **Non-Deterministic Outputs:** Asking an LLM the same question twice yields slightly different phrasing.
2. **Subjectivity & Lack of Ground Truth:** There is no mathematical "correct" answer for whether two complex personalities should date.
3. **Multi-Turn State Explosions:** Onboarding involves dynamic branching, adaptive probing, and follow-up caps across multiple conversation turns.
4. **Prompt Regression Risk:** Changing a prompt to fix an issue for Persona A might silently break extraction for Persona B.

---

## 2. Belong's Automated Testing & Evaluation Architecture

To solve this, Belong implements an automated **Synthetic Persona Simulation Harness** (`tests/simulators/` and `tests/simulations/`):

```
+----------------------------------------------------------------------------------------------------+
|                               BELONG EVALUATION & SIMULATION HARNESS                               |
+----------------------------------------------------------------------------------------------------+

  [ Golden Personas ]           [ Expected Outcomes ]
 (tests/fixtures/personas.json) (tests/fixtures/expected_outcomes.json)
           |                              |
           v                              |
  +--------------------------------+      |
  |     UserSimulator Actors       |      |
  |  - Simulates Alice, Bob, Eve   |      |
  |  - Drives multi-turn chat turns|      |
  |  - Answers onboarding prompts  |      |
  +---------------+----------------+      |
                  |                       |
                  | HTTP Dialogue Turns   |
                  v                       |
  +--------------------------------+      |
  |     Belong API & Workers       |      |
  |  - LangGraph Onboarding Agent  |      |
  |  - Signal Extraction & Vectors |      |
  |  - Stage 1 SQL + Stage 2 LLM   |      |
  +---------------+----------------+      |
                  |                       |
                  | Persisted Matches     |
                  v                       v
  +--------------------------------------------------------------------------------------------------+
  |                                INVARIANT VERIFICATION ENGINE                                     |
  |                                                                                                  |
  |  1. Complementary Pairing   : Alice + Bob       --> Assert Verdict == 'strong_alignment'         |
  |  2. Dealbreaker Defense     : Eve + Frank       --> Assert Dealbreaker Caught & Verdict != Strong|
  |  3. Conflict Clash          : Ian + Julia       --> Assert Conflict on 'conflict_style' dimension|
  |  4. Geographic Isolation    : Quinn + Ryan      --> Assert Filtered in Stage 1 (0 LLM tokens)    |
  +--------------------------------------------------------------------------------------------------+
```

---

## 3. The 4 Behavioral Persona Invariants

Rather than asserting exact text strings, Belong evaluates **Behavioral Invariants** across carefully crafted golden personas:

| Test Case | Personas Evaluated | Dynamic Tested | Expected Outcome & Invariant |
| :--- | :--- | :--- | :--- |
| **1. Complementary Pairing** | **Alice + Bob** | Alice needs calm reassurance during distress; Bob naturally provides grounding, patient acts of service. | • Stage 1: Reciprocal cosine score $> 0.80$<br>• Stage 2: `overall_verdict == "strong_alignment"`<br>• Reciprocity score $> 0.85$ |
| **2. Dealbreaker Defense** | **Eve + Frank** | Eve is an avid non-smoker with a strict dealbreaker; Frank is a heavy daily smoker. Both share identical hobbies (hiking, jazz). | • Stage 1: Vector recall retrieves them due to shared hobby text.<br>• Stage 2: **Instant exclusion!** `dealbreaker_violations` contains smoking; overall verdict cannot be `strong_alignment`. |
| **3. Conflict Style Clash** | **Ian + Julia** | Ian has an anxious communication style (needs immediate resolution); Julia is an avoidant stonewaller (withdraws under pressure). | • Dimension `conflict_style` must have verdict `conflict`.<br>• `potential_conflicts` cites evidence from both users' transcripts. |
| **4. Geographic Boundary** | **Quinn (Seattle) + Ryan (SF)** | Both have 50km radius limit; physical distance is ~1,100km. | • **Stage 1 SQL Filter excludes pair immediately.**<br>• Stage 2 LLM is **never called** (protects token budget). |

---

## 4. The User Simulator (`UserSimulator`)

Located in `tests/simulators/user_simulator.py`:
* Instead of hiring human testers to click through 10-minute onboarding flows, the `UserSimulator` class takes a persona specification (background, communication style, emotional needs, dealbreakers) and acts as an automated conversational agent.
* When the Belong onboarding bot asks: *"When there's a disagreement, how do you handle it?"*, the simulator generates in-character responses matching that persona.
* **Why this is critical:** It allows continuous integration (`pytest`) to run complete multi-turn onboarding flows on every code commit or prompt update.

---

## 5. Invariant Property Testing (`test_onboarding_invariants.py`)

Belong enforces hard non-negotiable constraints on the AI system:

### 1. The Follow-up Cap Invariant
* **Rule:** Users must never be asked more than 2 follow-up probes across the entire session.
* **Test:** Simulators intentionally send vague 1-word answers (*"idk"*, *"cool"*, *"fine"*).
* **Assertion:** `assert state["follow_up_count"] <= 2`. After 2 follow-ups, the graph must advance regardless of answer depth.

### 2. Clinical Confidence Floor
* **Rule:** No hallucinated or low-confidence inference may pollute the profile.
* **Test:** Inject borderline statements.
* **Assertion:** Verify in `profiles.profile` that no signal has `confidence < 0.50`.

### 3. Verbatim Quote Grounding
* **Rule:** Every extracted signal must have a quote that is a literal substring of what the user typed.
* **Test:** Compare `signal["quote"]` against raw conversation messages.
* **Assertion:** `assert signal["quote"].lower() in raw_user_message.lower()`.

---

## 6. Stage 1 Candidate Retrieval Benchmarking (`evaluate_stage1_retrieval.py`)

Located in `tests/evaluate_stage1_retrieval.py`:
* Evaluates Stage 1 performance across the entire database without running expensive LLM calls.
* **Metrics Tracked:**
  * **Recall@15:** Did the true complementary match appear in the top 15 shortlist?
  * **Candidate Pool Latency:** Total execution time of the hybrid SQL + vector cosine query (target: $< 25\text{ ms}$).
  * **Ranking Snapshot Diffs:** Compares candidate rank orders against previous snapshots (`tests/results/snapshots/`) to detect unintended ranking drift when tuning `bidirectional_weight`.

---

## 7. Scaling Belong to 100,000+ Users (System Evolution)

When the interviewer asks: *"How would this architecture scale as the userbase grows from 1,000 to 1,000,000 users?"*

```
+-----------------------------------------------------------------------------------+
|                        SCALING ROADMAP: 1K TO 1M USERS                            |
+-----------------------------------------------------------------------------------+

 1. Database Tier (PostgreSQL):
    - Introduce PostGIS: Replace Haversine trigonometric formula in SQL with
      a PostGIS geography(Point, 4326) column and GiST spatial index (ST_DWithin).
    - Read Replicas: Route read-heavy GET /api/matches and profile fetches to
      Postgres read replicas, reserving primary for onboarding writes and job claims.

 2. Asynchronous Workers:
    - RabbitMQ Partitioning: Scale belong-workers horizontally across a Kubernetes
      Deployment (HPA based on queue depth).
    - Batch Inference: Evaluate Stage 2 pairs concurrently using asyncio.gather with
      rate-limit semaphores.

 3. Vector Search Optimization:
    - Dedicated Vector Partitioning: Shard users by geographic region / metropolitan
      area so vector searches only index candidates within eligible physical range.
    - Two-Tier Re-ranking: Add a lightweight cross-encoder (bge-reranker-base)
      to filter 50 candidates down to 5 before calling the 70B LLM.
```

---

## 8. High-Impact Interview Soundbites

* *"I treat behavioral invariants the way financial systems treat balance invariants: an avoidant-anxious match must never produce a strong alignment verdict, and dealbreakers must trigger zero-tolerance exclusion."*
* *"I don't test LLMs by comparing string outputs; I test the system by simulating multi-persona communities and asserting structural and psychological properties on the resulting matches."*
* *"By decoupling Stage 1 vector recall from Stage 2 LLM reasoning, the system achieves sub-20ms candidate retrieval while keeping per-user matching costs under one cent."*
