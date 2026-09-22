# Update 2: Confidence Calibration, Reciprocal Matching Direction & Evidence ID Anchoring

**Date**: 2026-09-22
**Files Changed**: `onboarding/prompts.py`, `onboarding/graph.py`, `config.py`, `belong-workers/matching/schemas.py`, `belong-workers/matching/compatibility.py`

---

## Problem

Four architectural issues were identified after the first round of simulation analysis:

### 1. LLM Confidence Was Meaningless
Every extracted signal received a confidence of `0.95`–`1.0` regardless of how strongly the user's words supported it. The prompt only said `"Float between 0.8 and 1.0"`. As a result:
- Weak inferences were treated as hard evidence
- `"I like hiking"` became `"Values an active lifestyle"` at confidence `0.95` — an invention
- There was no way for downstream matching to distinguish things the user explicitly said vs. things the model guessed

### 2. Matching Direction Was Wrong
The pairwise reasoning prompt told the model to do "bidirectional evaluation" but left interpretation up to it. The model was allowed to compare `A.wants ↔ B.wants`, treating two people wanting the same thing as evidence of compatibility. This conflates **similarity** with **complementarity**.

The correct relationship model for a dating app is:
> Alice wants emotional reassurance → Does Bob *provide* that?

Not:
> Alice wants emotional reassurance → Does Bob also want emotional reassurance?

### 3. Evidence Was Hallucinated
The reasoning model generated free-text evidence strings like `"Bob's trail running suggests he may prefer solo activity"` — a fabrication. There was no way to trace a reasoning verdict back to actual user quotes.

### 4. Similarity and Complementarity Were Conflated
The output had a single `strong_alignments` list that mixed two different signals:
- **Shared taste**: "Both enjoy active lifestyles"
- **Reciprocal fulfillment**: "Alice needs reassurance; Bob explicitly provides it"

These are fundamentally different — the second is the product's core thesis.

---

## What This Update Solves

1. **Confidence is calibrated** with explicit bands and anchored examples. The model knows `0.99` means word-for-word and `0.50` means loose inference.
2. **`evidence_type` field** (`explicit` / `strong_inference` / `weak_inference`) lets downstream code filter what's eligible for matching.
3. **Signals below confidence `0.25` are dropped** at extraction time.
4. **Each extracted signal now has a deterministic `id`** (e.g. `q2_emotional_needs_s_emotional_needs_00`) persisted in the profile JSON.
5. **The pairwise reasoning prompt** now has an explicit `A.wants ↔ B.self` reciprocal mapping table and forbids comparing `A.wants ↔ B.wants` as evidence of compatibility.
6. **DimensionDetail** now uses `evidence_a_ids`/`evidence_b_ids` (lists of signal IDs) instead of invented free-text strings. The application resolves IDs to actual quotes.
7. **`PairwiseCompatibilityOutput`** now separates `complementary_alignments` (A needs X, B provides X) from `shared_alignments` (both want the same thing), and adds `reciprocity_score`.

---

## Changes Made

### `belong-api/onboarding/prompts.py`
- Added `CONFIDENCE CALIBRATION RUBRIC` section with five bands (0.95–1.00 down to <0.25)
- Added calibration examples showing correct vs. incorrect extraction
- Added `EVIDENCE TYPE RULES` section defining `explicit`, `strong_inference`, `weak_inference`
- Updated extraction item schema to include `evidence_type` field
- Changed confidence instruction from `"Float between 0.8 and 1.0"` to rubric reference

### `belong-api/onboarding/graph.py`
- Reads `evidence_type` and `confidence` from extracted items
- Drops signals where `confidence < 0.25` (insufficient evidence)
- Generates deterministic `signal_id` per signal: `{topic_id}_{field_abbrev}_{index:02d}`
- Stores `id` and `evidence_type` alongside existing signal fields

### `belong-api/config.py`
- Completely rewrote `PAIRWISE_REASONING_PROMPT_TEMPLATE`
- Added `PROFILE STRUCTURE` section explaining `self`/`wants`/`constraints`
- Added `RECIPROCAL MATCHING RULES` table with explicit `A.wants ↔ B.self` field mappings for all 5 dimensions
- Added strict rule: **Never compare A.wants against B.wants as evidence of reciprocal compatibility**
- Added `SIMILARITY vs. COMPLEMENTARITY` distinction instruction
- Instructed model to return `evidence_a_ids`/`evidence_b_ids` (not free-text)

### `belong-workers/matching/schemas.py`
- `DimensionDetail`: replaced `evidence_a: str` / `evidence_b: str` with `evidence_a_ids: List[str]` / `evidence_b_ids: List[str]` + `reasoning: str`
- `PairwiseCompatibilityOutput`: replaced `strong_alignments` with `complementary_alignments` + `shared_alignments`, added `reciprocity_score: float`

### `belong-workers/matching/compatibility.py`
- Added `_build_signal_index(profile)` — flat `{signal_id: quote}` dict built from a profile's signal lists
- Updated `validation_node` to build index for both profiles and resolve cited IDs → actual quotes, stored as `resolved_evidence` in graph state

---

## Verification

All graphs compiled and schema fields verified:

```text
onboarding_graph OK: <langgraph.graph.state.CompiledStateGraph object>
evidence_type in prompt: True
confidence rubric in prompt: True

compatibility_agent OK: <langgraph.graph.state.CompiledStateGraph object>
DimensionDetail fields: ['verdict', 'evidence_a_ids', 'evidence_b_ids', 'reasoning']
PairwiseCompatibilityOutput fields: ['overall_verdict', 'dimension_results',
  'complementary_alignments', 'shared_alignments', 'potential_conflicts',
  'dealbreaker_violations', 'uncertainties', 'reciprocity_score']
Signal index test: {'q2_s_emotional_needs_00': 'I need reassurance'}
```
