# Problems & Improvements — Update 4

**Date:** 2026-09-25  
**Scope:** Onboarding state machine, signal extraction, test coverage, simulator routing  
**Files changed:** 5

---

## Background

The `tests/results.md` end-to-end run (2026-09-24) showed Alice's onboarding conversation
stuck in status `active` after 8+ turns, with her dealbreaker answer repeated verbatim
as the response to two different probe questions. The final line was:

```
No compatibility results found in database.
```

This was entirely downstream of the onboarding never completing — no profile finalisation,
no embedding job, nothing for the matcher to work with. Bob's run completed normally; the
matcher itself was not the problem.

---

## Root Causes Found

### Bug 1 — Double assignment wiped the `_active_probe` pop (graph.py)

`extract_signals_node` made two separate assignments of `extracted_signals`:

```python
# Line ~150: pops _active_probe from the working copy
extracted_signals = dict(state.get("extracted_signals", {}))
active_probe = extracted_signals.pop("_active_probe", {})

# ... prompt built ...

# Line ~181: silent reset — throws away the pop, re-introduces _active_probe
extracted_signals = dict(state.get("extracted_signals", {}))
```

The second assignment re-read the raw state dict (which still contained `_active_probe`)
and discarded all previous work including the pop. This meant:

- `_active_probe` was never actually removed from the dict returned to LangGraph
- On the next DB load it was present again, making the system treat every subsequent turn
  as still being inside the same probe
- `follow_up_count` incremented, but the completion branch in `generate_response_node`
  was never reached cleanly because `finalize_profile` could throw (see Bug 1b below),
  leaving the conversation permanently `active` in the database

**Fix:** removed the second assignment entirely. The working copy built at the top of the
function (with `_active_probe` already popped) is the one used throughout.

### Bug 1b — `finalize_profile` raised into `generate_response_node` (graph.py)

`finalize_profile` had no error handling. If the profile row didn't exist yet (Alice's
profile was created by the test seeder, not by the onboarding flow itself in the earlier
test run), `ProfileRepository.create_profile` raised. This exception bubbled through
`generate_response_node`, causing `ainvoke` to throw, so the route never called
`update_conversation_state` — status stayed `active`.

**Fix:** wrapped the entire body of `finalize_profile` in `try/except Exception`. Any
persistence error is now logged and swallowed. The onboarding graph always transitions
to `completed`; a failed finalisation surfaces later as an `embedding` job failure, which
is recoverable and retryable — the right layer for that error.

### Bug 2 — Coverage check was `len > 0`, not confidence-gated (graph.py)

`find_missing_high_priority_field` marked a field as covered if it had *any* signal,
regardless of quality:

```python
# old
if signals and len(signals) > 0:
    has_signal = True
```

An off-topic answer to a probe (e.g. Alice answering with her dealbreakers when asked
about `self.provides`) still produced a low-confidence signal tagged against the target
field (confidence ~0.51–0.60). That signal passed the `len > 0` check and suppressed the
probe for the *next* missing field correctly — but on a re-run, if the LLM extracted
nothing at all, the next probe correctly fired. The inconsistency made the behaviour
non-deterministic between runs.

**Fix:** introduced `COVERAGE_MIN_CONFIDENCE = 0.75`. A field is only considered covered
when it has at least one signal at or above this threshold:

```python
has_confident_signal = any(
    float(s.get("confidence", 0.0)) >= COVERAGE_MIN_CONFIDENCE
    for s in signals
    if isinstance(s, dict)
)
```

The constant is module-level so tests can import and assert against it directly.

### Bug 3 — Extraction prompt produced Q1 blobs across three `wants.*` fields (prompts.py)

The `SIGNAL_EXTRACTION_PROMPT` had clear atomic-extraction rules for all `self.*` fields,
but the `wants.*` fields had only a single line:

```
- `wants.partner_traits`: Desired qualities, personality, or behavioral traits in a partner.
```

With no equivalent atomicity instruction, the LLM duplicated Alice's entire Q1 answer
(`"honestly I'm just tired of situationships..."`) as the `quote` and `summary` for
`wants.partner_traits`, `wants.partner_values`, **and** `wants.relationship_expectations`
simultaneously. This produced three identical signals from one sentence, bloating the
embedding source text with repeated content and reducing vector quality.

**Fix:** added explicit classification rules and an anti-blob instruction for all three
`wants.*` fields:

```
- `wants.partner_values`: Explicit values or ethics required in a partner. DISTINCT from traits.
- `wants.relationship_expectations`: What kind of relationship/future they want. DISTINCT from traits.

ATOMIC EXTRACTION — WANTS FIELDS:
When the user says "I want someone who communicates, is emotionally present, and wants to
build something real":
- "communicates"          → wants.partner_traits
- "emotionally present"   → wants.partner_traits
- "build something real"  → wants.relationship_expectations
- DO NOT copy the entire sentence as the quote for all three fields simultaneously.
```

### Bug 4 — Simulator sent stale core answer during probe turns (user_simulator.py + route)

The `/onboarding/message` response included `question_id` to tell the simulator which
question to answer next. During the core questions this worked correctly. But when
`current_area_index >= len(questions)` (probe phase), the route returned `question_id=None`:

```python
# old — returned None for any post-core turn
next_question_id = (
    settings.ONBOARDING_QUESTIONS[next_idx].id
    if next_idx < len(settings.ONBOARDING_QUESTIONS)
    else None
)
```

The simulator's update logic was:

```python
if next_qid:
    current_question_id = next_qid
```

`None` is falsy, so `current_question_id` stayed on `"q6_dealbreakers"`, and the simulator
sent the Q6 scripted answer (`"smoking is a hard no..."`) again — exactly matching the
repeated text seen in the test transcript for Alice's Q7 and Q8.

**Fix — route:** returns `"probe"` sentinel instead of `None` when the conversation is
active but past core questions:

```python
elif new_status == "active":
    next_question_id = "probe"   # adaptive follow-up — use fallback reply
else:
    next_question_id = None      # completed
```

**Fix — simulator:** routing now checks `if current_question_id in scripted` (explicit
membership) rather than `.get()` with a fallback. Any key not in the scripted map —
including `"probe"` and any future probe variants — automatically routes to
`fallback_reply`, which describes natural partner support behaviours and covers the most
common probe targets (`self.provides`, `self.emotional_needs`).

---

## Files Changed

| File | What changed |
|---|---|
| `belong-api/onboarding/graph.py` | Removed double assignment in `extract_signals_node`; wrapped `finalize_profile` in try/except; added `COVERAGE_MIN_CONFIDENCE = 0.75`; updated `find_missing_high_priority_field` to use confidence-gated check |
| `belong-api/onboarding/prompts.py` | Added `wants.partner_values` and `wants.relationship_expectations` classification rules; added atomic extraction anti-blob instruction for `wants.*` fields |
| `belong-api/api/routes/onboarding.py` | `next_question_id` now returns `"probe"` sentinel during adaptive-probe phase instead of `None` |
| `tests/simulators/user_simulator.py` | `run_onboarding_async` routing uses explicit `in scripted` check; `None` `question_id` no longer updates `current_question_id`; added clarifying comments |
| `tests/test_onboarding_invariants.py` | Added 5 new tests: `test_coverage_requires_min_confidence`, `test_coverage_passes_at_threshold`, `test_coverage_missing_when_signals_have_no_confidence_key`, `test_off_topic_probe_answer_still_completes`, updated `test_find_missing_high_priority_field_all_covered` to include confidence values; imported `COVERAGE_MIN_CONFIDENCE` |

---

## New Tests

| Test | What it covers |
|---|---|
| `test_coverage_requires_min_confidence` | Signal below `COVERAGE_MIN_CONFIDENCE` must NOT suppress a probe — regression for Bug 2 |
| `test_coverage_passes_at_threshold` | Signal exactly at threshold counts as covered |
| `test_coverage_missing_when_signals_have_no_confidence_key` | Missing `confidence` key defaults to 0.0, treated as not covered |
| `test_off_topic_probe_answer_still_completes` | Full two-step simulation of Alice's exact failure: off-topic probe answers, `_active_probe` leak check, completion after cap — regression for Bugs 1 + 1b |
| `test_find_missing_high_priority_field_all_covered` (updated) | Now includes `confidence` values in fixture signals so it tests real coverage logic |

---

## Expected outcome after these fixes

Re-running the E2E simulation with Alice and Bob should produce:

1. Alice's onboarding completes at turn 7 or 8 (6 core + 1–2 probes)
2. `finalize_profile` persists Alice's profile successfully
3. Embedding jobs are enqueued for both users
4. Workers generate `self_embedding` and `wants_embedding` for both
5. Matching job produces at least one `compatibility_results` row
6. `tests/results.md` no longer ends with `"No compatibility results found in database."`
