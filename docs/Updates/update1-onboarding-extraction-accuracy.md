# Update 1: Onboarding Extraction Accuracy & Profile Coverage Validation

**Date**: 2026-09-22
**Commit**: `61ff6bf`
**Files Changed**: `onboarding/prompts.py`, `onboarding/graph.py`, `config.py`

---

## Problem

During simulation testing (see `results.md`), the onboarding pipeline was discovered to have two critical failure modes:

### 1. Signal Extraction Misclassification
The LLM extractor was not respecting semantic boundaries between profile fields, leading to systematic misclassification. Common errors:
- `"I enjoy hiking"` → incorrectly placed in `self.values` or `self.lifestyle` instead of `self.interests`
- `"I am calm and dependable"` → incorrectly placed in `self.provides` instead of `self.personality_signals`
- Traits the user described about themselves placed in `wants.partner_traits`
- Empty target fields caused the model to "fill" them with content that didn't belong there

**Root cause**: The extraction prompt was too vague — it listed field names but gave the LLM no contract for what belongs in each field vs. what doesn't.

### 2. Missing High-Priority Profile Fields
Certain high-priority fields (`self.provides`, `self.emotional_needs`, `self.conflict_style`, `constraints.dealbreakers`) were being left empty without any follow-up. The pipeline went straight from core questions → profile finalization, with no mechanism to detect coverage gaps.

For example, a user who answered Q3 about conflict style but never explicitly described what they "bring" to a relationship would end up with `self.provides = []` — a critical gap for matching.

---

## What This Update Solves

1. **Fixes extraction accuracy** by giving the LLM an explicit classification contract with positive and negative examples for each field, and enforcing a strict rule: do not move data into the wrong category just because the intended field is empty.

2. **Refines onboarding question prompts** so each question is worded to directly elicit the intended signals (e.g. Q3 now explicitly asks *"what do you bring to a relationship as a partner?"* to surface `self.provides`).

3. **Adds adaptive profile coverage validation** after all core questions complete — if high-priority fields are still empty, the system generates targeted follow-up probes before finalizing the profile.

---

## Changes Made

### 1. Enhanced Extraction Prompt & Disambiguation Rules
**File**: `belong-api/onboarding/prompts.py`

Added explicit **Category Classification Contract & Rules**:

| Field | Put here when... | NOT here when... |
|---|---|---|
| `self.values` | Explicitly states principles, ethics, or moral stances | Hobbies/activities |
| `self.lifestyle` | How they live, daily routines, habits | One-off hobbies |
| `self.interests` | Things they enjoy doing, hobbies, passions | General personality traits |
| `self.life_goals` | Future aspirations, career/family plans | Current relationship preferences |
| `self.provides` | Explicitly states what they bring/give to a partner | Traits merely describing themselves |
| `self.conflict_style` | How they handle disagreements | General personality |
| `self.emotional_needs` | What they NEED FROM A PARTNER during stress | What they provide to a partner |
| `wants.partner_traits` | Desired qualities in a partner | Their own traits |

Added **few-shot category disambiguation examples** (positive + negative) for each field.

Added **strict empty-category rule**: Do NOT move information into another category simply because the intended field is empty. Empty fields are valid.

---

### 2. Updated Onboarding Questions & Target Dimensions
**File**: `belong-api/config.py`

| Question | Change | Target Fields Updated |
|---|---|---|
| Q1 | Unchanged | Added `wants.partner_values` |
| Q2 | "When things get stressful, what do you need **and what helps you feel supported?**" | Same |
| Q3 | **"When there's a disagreement, how do you usually handle it? And what do you feel you bring to a relationship as a partner?"** | Same — `provides` intent made explicit |
| Q4 | "What does your day-to-day look like, what do you enjoy doing, and **what values or future goals are important to you?**" | Added `self.life_goals` |
| Q5 | Unchanged | Same |
| Q6 | "What are **non-negotiable dealbreakers or absolute hard constraints** for you in a partner?" | Same |

---

### 3. Profile Coverage Validator & Adaptive Probes
**File**: `belong-api/onboarding/graph.py`

Implemented `HIGH_PRIORITY_FIELDS` list and `find_missing_high_priority_field(extracted_signals)` utility.

**High-priority fields checked (in priority order)**:
1. `self.provides`
2. `self.emotional_needs`
3. `self.conflict_style`
4. `constraints.dealbreakers`
5. `wants.partner_traits` / `wants.relationship_expectations`

**New flow after core questions complete**:
```
Core Q1-Q6 answered
        ↓
Coverage validator: find_missing_high_priority_field(signals)
        ↓
  Missing field?
   /          \
 yes           no
  ↓             ↓
Adaptive     Finalize
 probe       profile
  ↓
Extract signals from adaptive probe response
  ↓
Coverage validator (again, up to max_probes limit)
```

`extract_signals_node` was also updated to handle adaptive probe turns (when `current_area_index >= len(questions)`) by targeting all high-priority field dimensions in the extraction prompt.

---

## Verification

Graph compiled cleanly and coverage validator correctly identifies missing fields:

```text
Graph compiled successfully! <langgraph.graph.state.CompiledStateGraph object>
Coverage test (empty signals): {'keys': ['self.provides'], 'topic': 'What You Provide to a Partner', 'prompt': 'And separately, what do you feel you bring to a relationship as a partner?'}
```
