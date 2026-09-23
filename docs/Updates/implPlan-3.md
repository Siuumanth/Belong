# Implementation Plan: Fix Onboarding Follow-Up Loop, State Freshness, Atomic Extraction & Reasoning

This plan addresses all issues identified in `tests/results2-good.md`:
1. **🔴 P0 — Follow-up loop termination** (`MAX_FOLLOWUPS = 2` hard cap, status `completed`, never Q9/Q10).
2. **🔴 P0 — Coverage state freshness** (extract → merge into state → coverage check on updated state → decide next node).
3. **🔴 P0 — Restore atomic extraction** (individual signals, verbatim quotes, valid labels/IDs/question_ids, no `"survey response"` placeholder).
4. **🟠 P1 — Keep reciprocal reasoning and separate `complementary_alignments` from `shared_alignments`**.
5. **🟠 P1 — Prevent unsupported over-inference** in reasoning prompts and schemas.
6. **🟡 P2 — Behavioral `provides` adaptive question probe**.
7. **🟡 P2 — Prevent duplicate follow-up dimensions** (`followups_asked` / `probe:{dim}` tracking).

---

## User Review Required

> [!IMPORTANT]
> - `MAX_FOLLOW_UPS` is strictly enforced as a maximum of 2 follow-ups across the entire onboarding session. Total user answers will never exceed 8 (6 core + max 2 follow-ups).
> - Compatibility reasoning output will explicitly separate `complementary_alignments` (reciprocal fulfillment: A wants X → B provides Y) and `shared_alignments` (similarity: both like outdoor activities), while preserving `strong_alignments` in the database for backward compatibility.
> - The mock fallback in `user_simulator.py` which was generating the blob `{"summary": "...", "evidence": "survey response", "confidence": 0.9}` will be replaced with atomic signals and realistic verbatim quotes.

---

## Proposed Changes

### Component 1: Onboarding State & Graph Engine (`belong-api`)

#### [MODIFY] [belong-api/onboarding/state.py](file:///d:/code/Golang/Belong/belong-api/onboarding/state.py)
- Add `active_probe_field: Optional[str]` and `active_probe_prompt: Optional[str]` to `OnboardingState` so that when an adaptive probe is answered, the extractor knows precisely what probe was asked.

#### [MODIFY] [belong-api/onboarding/graph.py](file:///d:/code/Golang/Belong/belong-api/onboarding/graph.py)
- **Behavioral Probe Question**: Update `HIGH_PRIORITY_FIELDS` for `self.provides` to:
  `"What are some things you naturally do for a partner? For example, how do you support them, communicate with them, or show up when they're having a difficult time?"`
- **Duplicate Probe Guard**: Update `find_missing_high_priority_field(extracted_signals, covered_areas)` to ignore fields that were already probed (`f"probe:{spec['keys'][0]}" in covered_areas`).
- **State Freshness & Contextual Extraction**:
  - In `extract_signals_node`:
    - Identify the question text being answered (`questions[current_idx].prompt` for core questions, or `active_probe_prompt` for adaptive probes).
    - Pass both question text and target dimensions to `SIGNAL_EXTRACTION_PROMPT`.
    - If user answered a `self.provides` probe, ensure extracted support actions are classified under `self.provides`.
    - Filter out weak signals with confidence `< 0.50`.
    - Merge newly extracted signals into `extracted_signals`.
    - Clear active probe tracking and return updated `extracted_signals`.
- **Follow-up Termination & Coverage Evaluation**:
  - In `generate_response_node`:
    - Evaluate coverage against the freshly merged `extracted_signals`.
    - When all core questions are answered (`current_idx >= len(questions)`):
      ```python
      missing = find_missing_high_priority_field(extracted_signals, covered_areas)
      coverage_passed = (missing is None)

      if coverage_passed or follow_up_count >= MAX_FOLLOWUPS:
          await finalize_profile(state)
          return {
              "status": "completed",
              "follow_up_count": follow_up_count,
              "latest_assistant_response": conclusion_message,
              ...
          }
      else:
          new_follow_up_count = follow_up_count + 1
          assert new_follow_up_count <= MAX_FOLLOWUPS
          covered_areas.append(f"probe:{missing['keys'][0]}")
          return {
              "status": "active",
              "follow_up_count": new_follow_up_count,
              "active_probe_field": missing["keys"][0],
              "active_probe_prompt": missing["prompt"],
              ...
          }
      ```
    - Enforce hard invariant: `assert follow_up_count <= MAX_FOLLOWUPS`.
    - Ensure `generate_response_node` returns `extracted_signals` so routes persist it to DB.

#### [MODIFY] [belong-api/onboarding/prompts.py](file:///d:/code/Golang/Belong/belong-api/onboarding/prompts.py)
- Update `SIGNAL_EXTRACTION_PROMPT` to include:
  - `QUESTION ASKED: "{question_text}"`.
  - Atomic signal requirement: each distinct activity, trait, or value must be extracted as a separate atomic item with its own exact quote, label, summary, and confidence.
  - Prohibit giant blobs and generic evidence placeholders.
  - Calibrated confidence bands: 0.95–1.00 explicit, 0.75–0.94 strong inference, 0.50–0.74 reasonable inference, <0.50 drop.

---

### Component 2: Pairwise Reciprocal Reasoning & Alignment Separation (`belong-workers` & `belong-api`)

#### [MODIFY] [belong-workers/config.py](file:///d:/code/Golang/Belong/belong-workers/config.py) & [belong-api/config.py](file:///d:/code/Golang/Belong/belong-api/config.py)
- Update `PAIRWISE_REASONING_PROMPT_TEMPLATE`:
  - Reciprocal Matching Rules: `A.wants ↔ B.self.provides` and `B.wants ↔ A.self.provides`.
  - Strict separation of `complementary_alignments` (reciprocal fulfillment: A wants X → B provides Y) and `shared_alignments` (mutual similarity: both like hiking, both in tech).
  - Over-inference prevention: Explicitly warn against assuming "calm" or "thoughtful" equates to "active listening" or "reassurance". Mark unsupported inferences under `uncertainties`.
  - Citations must strictly reference signal IDs (`evidence_a_ids`, `evidence_b_ids`).

#### [NEW] [belong-api/db/migrations/006_add_alignments_to_compatibility_results.sql](file:///d:/code/Golang/Belong/belong-api/db/migrations/006_add_alignments_to_compatibility_results.sql)
- Add `complementary_alignments` and `shared_alignments` JSONB columns to `compatibility_results`.

#### [MODIFY] [belong-workers/workers/matching_worker.py](file:///d:/code/Golang/Belong/belong-workers/workers/matching_worker.py)
- Persist `complementary_alignments`, `shared_alignments`, and `strong_alignments` into `compatibility_results`.

#### [MODIFY] [belong-api/api/routes/matches.py](file:///d:/code/Golang/Belong/belong-api/api/routes/matches.py)
- Return `complementary_alignments` and `shared_alignments` in `MatchCandidateResponse`.

---

### Component 3: Test Simulator & Invariant Verification (`tests`)

#### [MODIFY] [tests/simulators/user_simulator.py](file:///d:/code/Golang/Belong/tests/simulators/user_simulator.py)
- In `PersonaBuilder.build()`: Replace the dummy blob (`"evidence": "survey response"`, `confidence: 0.9`) with structured atomic signals using verbatim quotes from responses, labels, IDs, and calibrated confidence.
- In `UserSimulator.run_onboarding_async()`:
  - When responding to probes asking about partner support/provides, use behavioral responses: e.g. `"I listen patiently when my partner is stressed, offer calm reassurance, communicate transparently, and make time to support their goals."`
  - Cap loop turns to prevent infinite polling.

#### [MODIFY] [tests/get_latest_results.py](file:///d:/code/Golang/Belong/tests/get_latest_results.py)
- Fetch and display `complementary_alignments` and `shared_alignments` separately in the inspection report.

#### [NEW] [tests/test_onboarding_invariants.py](file:///d:/code/Golang/Belong/tests/test_onboarding_invariants.py)
- Automated unit test asserting:
  - 6 core questions + max 2 follow-ups = maximum 8 user turns.
  - Never reaches Q9 or Q10.
  - `status == "completed"` triggers upon coverage pass or reaching `MAX_FOLLOWUPS`.
  - No duplicate follow-up probes asked for the same dimension.
  - Extracted signals in DB are atomic and have valid quotes, IDs, and confidence >= 0.50.

---

## Verification Plan

### Automated Tests
Run pytest targeting the new invariant test:
```powershell
pytest tests/test_onboarding_invariants.py -v
```
Run existing simulation tests:
```powershell
pytest tests/simulations/test_user_onboarding_simulation.py -v
```

### Manual Verification
- Run `tests/run_custom_simulation.py` with Alice and Bob.
- Run `python tests/get_latest_results.py` to generate `tests/results.md` and verify:
  1. Bob and Alice onboarding status is `completed` (never `active`).
  2. Dialogues end at <= 8 turns (never Q9 or Q10).
  3. Extracted Profile JSON in `profiles` contains atomic signals with real quotes, labels, IDs (no `"evidence": "survey response"`).
  4. Compatibility Result separates `complementary_alignments` and `shared_alignments` cleanly without over-inferring "active listening" from "calm".
