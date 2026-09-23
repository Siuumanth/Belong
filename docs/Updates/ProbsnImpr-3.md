Yes. Taking the latest run and the previous run together, the **current Belong problems** are much clearer now.

I'd separate them into **functional bugs**, **extraction regressions**, and **reasoning/output issues**.

## Current problem list

### 🔴 P0 — Onboarding gets stuck in a follow-up loop

This is the most serious problem.

Bob reaches Q7, then gets essentially the same `provides` question repeatedly at Q8, Q9, Q10 with the same answer, while the conversation remains `active`. 

The intended invariant is:

```text
MAX_FOLLOWUPS = 2
```

but the actual behavior is:

```text
missing provides
    ↓
follow-up #1
    ↓
still missing provides
    ↓
follow-up #2
    ↓
still missing provides
    ↓
follow-up #3 ❌
    ↓
follow-up #4 ❌
```

### Fix

Make the graph have an explicit terminal condition:

```python
if core_questions_finished:
    if coverage_passed:
        complete()
    elif follow_up_count >= MAX_FOLLOWUPS:
        complete()
    else:
        ask_followup()
```

And **increment `follow_up_count` when the follow-up is generated**, not after some later step.

Also add a hard invariant:

```python
assert follow_up_count <= MAX_FOLLOWUPS
```

More importantly, test it.

### Test

```text
6 core questions
+ maximum 2 follow-ups
= maximum 8 user answers
```

Never Q9/Q10.

---

# 🔴 P0 — Coverage state isn't recognizing the new answer

This is related to the loop but technically a separate bug.

The user answers the `provides` question, yet coverage apparently still sees:

```text
self.provides = []
```

So it asks again.

There are two possibilities:

1. extraction isn't producing `provides`
2. extraction does produce it, but coverage is checking **stale state**

The latest run strongly suggests **both need investigation**.

### Fix

After every answer, the graph should do:

```text
answer
 ↓
extract signals
 ↓
MERGE extracted signals into state
 ↓
coverage check against UPDATED state
 ↓
decide next node
```

Not:

```text
answer
 ↓
coverage check
 ↓
extract later
```

And definitely not checking the state from before the current answer.

---

# 🔴 P0 — Extraction regressed to blob-level storage

This is probably the biggest data-quality regression.

Previous behavior:

```json
{
  "label": "Enjoys trail running",
  "quote": "Trail running",
  "summary": "...",
  "confidence": 1.0
}
```

Multiple atomic signals.

Current behavior:

```json
{
  "summary": "Trail running, coffee brewing, software engineering, and weekend trips.",
  "evidence": "survey response",
  "confidence": 0.9
}
```

One giant blob.

And `"survey response"` isn't evidence. It's just a placeholder.

That means you've lost the important properties:

```text
atomic signal
specific evidence
semantic category
meaningful confidence
```

### Fix

**Do not rewrite the extraction architecture. Revert the extraction output contract to the previous atomic-signal format**, then apply the new category-disambiguation rules on top of it.

Each signal should look roughly like:

```json
{
  "label": "Enjoys trail running",
  "quote": "Trail running",
  "summary": "The user enjoys trail running.",
  "confidence": 0.98,
  "question_id": "q4_lifestyle_values"
}
```

And:

```text
evidence.quote
```

must be the actual relevant text from the user's answer.

Never:

```text
"evidence": "survey response"
```

---

# 🔴 P1 — Confidence is effectively dead

The current run has:

```text
0.9
0.9
0.9
0.9
0.9
...
```

That's not confidence estimation.

But I **wouldn't make confidence calibration the next engineering task yet**.

First restore:

```text
atomic signals
+
real evidence
```

Then see what confidence actually looks like.

If it remains:

```text
0.9 everywhere
```

then fix calibration.

### Better eventual contract

```text
0.95–1.00 → explicitly stated
0.75–0.94 → strongly supported interpretation
0.50–0.74 → meaningful inference
<0.50 → weak / don't normally extract
```

But don't spend time tuning these numbers until the extraction output itself is correct.

---

# 🟠 P1 — The new reciprocal reasoning is actually good

**Keep this. Don't revert it.**

The latest reasoning is doing something important that the previous version wasn't:

```text
A wants X
       ↓
B has/provides Y
       ↓
does Y satisfy X?
```

And vice versa.

The `evidence_a_ids` / `evidence_b_ids` approach is also a good architectural improvement. 

So the correct approach is:

```text
OLD extraction ❌
NEW extraction contract
        ↓
NEW reciprocal reasoning ✅
```

Don't roll back the reasoning just because extraction regressed.

---

# 🟠 P1 — Similarity and complementarity are still mixed

This is subtle but important.

The reasoning output contains:

> "Both value active, outdoorsy lifestyles..."

That's a legitimate observation, but it's **similarity**:

```text
Alice self ↔ Bob self
```

It isn't:

```text
Alice wants ↔ Bob provides
```

Your product's interesting idea is the second one.

So change the output schema to explicitly separate them:

```json
{
  "complementary_alignments": [],
  "shared_alignments": [],
  "potential_conflicts": [],
  "uncertainties": []
}
```

### Example

```text
complementary_alignments:
- Alice wants active living → Bob provides an active lifestyle

shared_alignments:
- Both enjoy outdoor activities
- Both work in technology

potential_conflicts:
- ...

uncertainties:
- ...
```

That keeps **"similar people"** and **"people who satisfy each other's needs"** conceptually separate.

---

# 🟠 P1 — Reasoning is still allowed to over-infer

Even though reciprocal reasoning improved, the model is still making claims like:

> "A's need for active listening is met by B's thoughtful and calm disposition."

But:

```text
thoughtful ≠ active listening
calm ≠ active listening
```

Likewise:

> "B's need for clear reassurance is met by A's empathetic ... orientation."

Again:

```text
empathetic ≠ necessarily provides reassurance
```

The system needs to distinguish:

### Explicit

```text
Alice wants active listening
Bob says "I listen patiently"
```

→ strong complementary evidence.

### Reasonable inference

```text
Alice wants emotional safety
Bob says "I provide reassurance"
```

→ possibly strong/partial depending on wording.

### Unsupported

```text
Alice wants active listening
Bob says "I'm calm"
```

→ **unclear**, not strong alignment.

---

# 🟡 P2 — Your adaptive `provides` question isn't producing good evidence

This is partly a question-design issue.

The current question:

> "What do you feel you bring to a relationship as a partner?"

produced:

> "I value open communication, mutual respect, emotional honesty..."

That's mostly **values / expectations**, not concrete `provides` behavior.

So change the probe to something behavioral:

> **"What are some things you naturally do for a partner? For example, how do you support them, communicate with them, or show up when they're having a difficult time?"**

Now you're much more likely to get:

```text
"I listen when they're stressed."
"I reassure them."
"I make time for them."
"I communicate openly."
```

Those are excellent `provides` signals.

---

# 🟡 P2 — Don't let the same follow-up get regenerated

Even with `MAX_FOLLOWUPS`, you should have another guard:

```python
if followup_question == previous_followup_question:
    generate_alternative_probe()
```

Better yet, track covered/missing dimensions:

```json
{
  "followups_asked": [
    "self.provides"
  ]
}
```

Then:

```text
missing field = self.provides
already asked self.provides
→ don't ask self.provides again
→ either try alternative wording once
→ or count it toward follow-up cap and move on
```

This protects you against exactly the Q7→Q8→Q9→Q10 behavior.

---

# 🟡 P2 — The profile shouldn't be considered complete just because a field is non-empty

Eventually your coverage check should distinguish:

```text
missing
```

from:

```text
present but weak
```

For example:

```text
provides:
"I value mutual respect."
```

Technically present.

But it doesn't tell us much about **what the person provides**.

Whereas:

```text
provides:
"I listen patiently when my partner is stressed."
```

is strong evidence.

Don't build another LLM validator for this yet. Once atomic extraction + evidence is restored, a simple confidence/evidence threshold is enough for the first version.

---

# What I would NOT change right now

Don't touch:

* embedding architecture
* candidate retrieval
* RabbitMQ
* workers
* ranking
* database schema
* reciprocal reasoning architecture

Those aren't the current bottlenecks.

The current flow is:

```text
             🔴 BROKEN
        onboarding state
               +
        🔴 BROKEN
           extraction
               ↓
        🟢 GOOD
    reciprocal reasoning
```

So fix the first two and then reassess the third.

---

# Final priority

### 🔴 P0 — Fix immediately

**1. Follow-up termination**

* `MAX_FOLLOWUPS` hard cap
* correct `status = completed`
* no Q9/Q10
* increment counter correctly

**2. State freshness**

* extract → merge → coverage
* coverage must see the new extraction

**3. Restore atomic extraction**

* one signal per entry
* real verbatim evidence
* labels + summaries
* `question_id`
* no `"survey response"` placeholder

### 🟠 P1

**4. Keep reciprocal reasoning**

**5. Separate:**

```text
complementary_alignments
shared_alignments
```

**6. Prevent unsupported inference**

### 🟡 P2

**7. Improve `provides` adaptive question**

**8. Prevent duplicate follow-up dimensions**

**9. Revisit confidence calibration after extraction is fixed**

---

The key insight from these two runs is actually very good for the project:

**You now know that your reasoning layer can implement Belong's core reciprocal matching idea. The current failure is upstream: the onboarding state machine and profile representation aren't reliably feeding it the right structured evidence.**

That's a much more concrete engineering problem than "the AI matching isn't good."
