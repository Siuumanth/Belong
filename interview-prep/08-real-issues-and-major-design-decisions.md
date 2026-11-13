# 08. Real Engineering Issues & Major Design Decisions (The Battle-Tested Log)

> **The Actual Technical Hurdles, Root-Cause Investigations, and System Iterations**  
> *Everything documented here represents real bugs, empirical test failures, and design decisions carefully evaluated and resolved during the development of Belong. Speak to these in interviews to demonstrate authentic, senior-level systems engineering.*

---

## 1. Summary of Major Engineering Battles

| Issue # | Area | The Symptom / Bug | Root Cause | Engineering Solution |
| :---: | :--- | :--- | :--- | :--- |
| **01** | **Workers / Async Queue** | Matching completed with **0 candidate matches** despite successful user onboarding. | 11-second asynchronous race condition + Hugging Face DNS hang. | Active vector readiness polling + reduced HTTP timeout (3s) with fast offline fallback. |
| **02** | **LLM Reasoning & Groq** | Groq crashed with `tool_use_failed` (400), cascading into HTTP 429 and `JSONDecodeError`. | 2048 token limit truncated complex JSON; naive retry slammed rate limits with empty string. | Raised ceiling to 4096 tokens, regex-extracted `failed_generation` directly from error payload, added empty-response guard. |
| **03** | **Matching Architecture** | Model matched users who *wanted* the same things rather than users who *fulfilled* each other. | Conflating **similarity** with **complementarity**; prompt allowed `A.wants ↔ B.wants`. | Enforced strict `A.wants ↔ B.self` reciprocal table; separated `complementary_alignments` from `shared_alignments`. |
| **04** | **Extraction Quality** | LLM assigned confidence `0.95`–`1.0` to loose guesses (*"I like hiking"* $\rightarrow$ *"Values active lifestyle"* at 0.95). | Vague prompt instruction (*"Float between 0.8 and 1.0"*). | Built 5-band Confidence Calibration Rubric; added `evidence_type` (`explicit`/`inference`); filtered $< 0.50$. |
| **05** | **Profile Coverage** | Critical matching fields (`provides`, `emotional_needs`, `conflict_style`) were left empty. | Pipeline transitioned straight from questions to finalization without coverage validation. | Built `find_missing_high_priority_field()` validator to trigger dynamic, adaptive probes before wrapping up. |
| **06** | **Cost & Latency** | High time-to-first-token (TTFT) latency and frequent token quota exhaustion on Groq. | Prompts included raw profile JSON bloated with UUIDs, question keys, and confidence floats. | Implemented `_slim_profile` to strip metadata before LLM reasoning, slashing prompt tokens by **~50%**. |
| **07** | **Taxonomy Rigidity** | Users sharing novel or off-script psychological traits had their data dropped or forced into wrong fields. | Extraction prompt was tightly coupled to hardcoded question IDs with no escape hatch. | Centralized schema taxonomy (`PROFILE_DIMENSIONS`), decoupled extraction, and added `other_signals` escape hatch. |
| **08** | **User Experience (UX)** | Compatibility reports sounded like clinical lab reports: *"User A wants X, User B provides X"*. | Third-person prompt instructions. | Rewrote prompt for **second-person voice ("You")**, making explanations warm and human-facing. |

---

## 2. Deep Dive: Issue 01 — The 11-Second Asynchronous Vector Race Condition

### The Symptom:
During automated multi-user simulations (`tests/run_custom_simulation.py`), user onboarding and trait extraction completed with high confidence ($0.98$). However, **`compatibility_results` remained completely empty (0 rows)** and matching runs finished with `candidate_count: 0`.

### The Investigation & Root Cause:
Tracing the execution logs uncovered a timing mismatch between two asynchronous pipelines:
1. When onboarding finished, the API queued an `embedding` job and the test executed a static `await asyncio.sleep(5)`.
2. Inside the background worker, `EmbeddingClient` attempted to call the Hugging Face Inference API. Due to Docker container DNS resolution stalls (`Temporary failure in name resolution`), the network request hung for **16 seconds** before timing out and falling back.
3. Meanwhile, after only 5 seconds, the test fired `POST /api/matches`.
4. Stage 1 candidate recall immediately executed:
   ```sql
   SELECT ... FROM profiles p WHERE p.self_embedding IS NOT NULL;
   ```
5. Because the worker had not yet written the embeddings, **0 profiles had vectors**. Stage 1 found 0 candidates and concluded the run.
6. 11 seconds later, the embedding worker finally finished and wrote vectors to Postgres—too late.

### The Solution:
1. **Active Readiness Polling:** Replaced fragile static `sleep(5)` timers with an active polling loop that checks Postgres until `embedding_source_text` is confirmed written before triggering matching.
2. **Aggressive Timeout & Fast Fallback:** Lowered the Hugging Face HTTP timeout in `EmbeddingClient` from 30s to **3.0s** (`wait_for_model=False`). If network or DNS lags, the worker immediately falls back to local deterministic embedding generation within 50ms.

---

## 3. Deep Dive: Issue 02 — Groq Token Truncation, Cascading 429s & Empty Content

### The Symptom:
When candidate recall did find a match, Stage 2 pairwise evaluation crashed with:
```text
Error code: 400 - {'error': {'message': 'Failed to parse tool call arguments as JSON', 'code': 'tool_use_failed'}}
json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

### The Investigation & Root Cause:
1. **Mid-Token Truncation:** The structured output schema `PairwiseCompatibilityOutput` (4 dimensions, evidence quotes, reciprocal scores, alignments, and narrative summaries) is token-intensive. With Groq's `max_tokens` set to `2048`, the model truncated mid-generation (e.g., closing brackets were missing).
2. **Cascading Failure:** When Groq's tool-call parser failed (400), our naive fallback attempted an immediate second plain LLM invoke.
3. This second invoke breached Groq's burst rate limits (`HTTP 429 Too Many Requests`).
4. After waiting out the rate limit, the API returned an HTTP 200 with an empty body (`content = ""`). Calling `json.loads("")` raised `JSONDecodeError`.

### The Solution:
1. **Raised Token Ceiling:** Increased `max_tokens` from `2048` to **`4096`** in `get_llm()` for Groq.
2. **`failed_generation` Extraction:** When Groq returns a `400 tool_use_failed`, it actually embeds the partially generated JSON in the error message string under `failed_generation`. Instead of throwing it away and making a secondary API call (which triggers rate limits), we use regex to extract and repair the JSON directly from the error payload.
3. **Empty-Response Guard:** Added an explicit content check in `_retry_llm_invoke`: if `content` is empty string, it triggers an immediate backoff retry instead of crashing the JSON parser.

---

## 4. Deep Dive: Issue 03 — The "Similarity vs. Complementarity" Trap

### The Symptom:
Two test personas who both had anxious attachment styles and both needed constant emotional reassurance were given a high compatibility score by the LLM reasoning agent.

### The Root Cause:
The early pairwise reasoning prompt asked the LLM to do "bidirectional evaluation" without concrete mapping constraints.  
The model evaluated `User A.wants ↔ User B.wants`:
* *"Alice wants emotional reassurance."*
* *"Bob also wants emotional reassurance."*
* *"Verdict: Strong Alignment! They share the same emotional needs!"*

This is a **fatal flaw in relationship psychology**: sharing the same need does NOT mean you can fulfill it. In reality, two partners who both withdraw or both demand reassurance under stress often escalate conflict.

### The Solution:
1. **Enforced Reciprocal Mapping Table:** Rewrote `PAIRWISE_REASONING_PROMPT_TEMPLATE` with strict rules:
   $$\text{Evaluate } \mathbf{User\ A.wants} \longleftrightarrow \mathbf{User\ B.self} \quad (\text{Can B fulfill A?})$$
   $$\text{Evaluate } \mathbf{User\ B.wants} \longleftrightarrow \mathbf{User\ A.self} \quad (\text{Can A fulfill B?})$$
2. **Explicit Prohibition:** Added a hard negative constraint: *"NEVER compare A.wants against B.wants as evidence of compatibility."*
3. **Separated Output Fields:** Split alignments into:
   * `complementary_alignments`: A needs X, B provides X (primary matching thesis).
   * `shared_alignments`: Both enjoy hiking or value personal growth (secondary shared taste).

---

## 5. Deep Dive: Issue 04 — Confidence Calibration & The "0.95 Guessing" Bug

### The Symptom:
In initial tests, every extracted trait received an artificially high confidence score (`0.95`–`1.0`). If a user said *"I like walking my dog"*, the extractor produced:
```json
{ "label": "Active outdoors lifestyle", "confidence": 0.98 }
```
Downstream matching treated this weak guess with the same weight as explicit core values.

### The Root Cause:
The prompt instruction merely stated: `"confidence: Float between 0.8 and 1.0"`. Because the model was given no reference anchor, it naturally gravitated toward the top of the range for every output.

### The Solution:
1. **5-Band Calibration Rubric:** Defined strict semantic boundaries in `onboarding/prompts.py`:
   * `0.95 - 1.00`: Word-for-word verbatim statement (*"I am an introvert"* $\rightarrow$ Introvert).
   * `0.80 - 0.94`: Direct paraphrase with unambiguous intent.
   * `0.60 - 0.79`: Reasonable inference backed by strong context.
   * `0.40 - 0.59`: Plausible guess; unverified hypothesis.
   * `< 0.40`: Speculative assumption.
2. **Hard Filtering:** Any signal with `confidence < 0.50` is dropped at extraction time.
3. **`evidence_type` Field:** Every signal is tagged as `explicit`, `strong_inference`, or `weak_inference`.

---

## 6. Deep Dive: Issue 05 — Signal Misclassification & The Empty Category Trap

### The Symptom:
Users answering questions about their morning routines had their hobbies placed into `self.values`. When users described their own personality, traits were placed into `wants.partner_traits`.

### The Root Cause:
LLMs dislike producing empty JSON arrays. When an extraction prompt listed categories without negative boundaries, the model felt compelled to "fill" empty arrays with unrelated content from the user's reply.

### The Solution:
1. **Category Classification Contract:** Added explicit boundary definitions:
   * `self.values`: Put here for principles/ethics. NOT for hobbies or one-off activities.
   * `self.provides`: Put here for what you DO for a partner. NOT for general personality.
   * `self.emotional_needs`: Put here for what you NEED from a partner. NOT for what you provide.
2. **The "Empty Fields Are Valid" Rule:** Added a strict instruction:
   > *"Do NOT move information into another category simply because the intended field is empty. Empty arrays are expected and valid."*
3. **Dynamic Coverage Probing:** If critical fields (`self.provides`, `self.emotional_needs`, `self.conflict_style`) remain empty after core questions, `find_missing_high_priority_field()` triggers an adaptive probe to ask the user directly rather than letting the LLM guess.

---

## 7. Deep Dive: Issue 06 — Profile Slimming for Token & Latency Optimization

### The Symptom:
Evaluating 15 candidate pairs in Stage 2 took over 30 seconds and periodically tripped Groq rate limits.

### The Root Cause:
The prompt passed complete raw profile JSON for User A and User B. This included database UUIDs (`q1_intent_s_values_00`), timestamps, question keys, and confidence numbers. For 15 candidates, this wasted thousands of tokens on bookkeeping metadata that had zero relevance to relationship compatibility.

### The Solution:
Built `_slim_profile(profile)` in `belong-workers/matching/compatibility.py`:
```python
def _slim_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    # Keeps ONLY: label, summary, quote, demographics (age, gender, goal)
    # Drops: UUIDs, question_ids, evidence_types, confidence floats
```
* **Result:** Reduced prompt size by **~50%**.
* **Impact:** Slashed Groq TTFT latency, eliminated rate-limit triggers, and kept per-batch reasoning costs under one cent.

---

## 8. Deep Dive: Issue 07 & 08 — Emergent Taxonomies & Second-Person Voice

### The Symptom:
1. When a user shared a profound, unique insight that didn't fit the 8 standard categories (e.g., spiritual philosophy or neurodivergent sensory habits), the extractor dropped it.
2. When match results were presented to users, the text read like a cold psychological evaluation of test subjects: *"User A is quiet. User B is supportive."*

### The Solution (Phase 11):
1. **Emergent Signal Escape Hatch (`other_signals`):** Decoupled extraction from rigid question IDs and added an `other_signals` array in the schema. Uncategorized insights are preserved, serialized into vectors, and evaluated during matching.
2. **Second-Person Voice ("You"):** Rewrote `PAIRWISE_REASONING_PROMPT_TEMPLATE` to address User A directly as **"You"** and refer to User B by their real name:
   > *"You need quiet space to recharge when stressed, which Alex naturally honors by providing steady, unhurried support without pressure to fix things immediately."*

---

## 9. How to Pitch These in an Interview (The Senior Engineer Framework)

When the interviewer asks: *"Tell me about a difficult technical challenge you faced on Belong."*

### Structure Your Answer Using This 4-Step Narrative:
1. **The Conflict (What broke?):**  
   *"During multi-user simulation testing, our matching pipeline suddenly started returning zero results, even though onboarding and extraction were succeeding."*
2. **The Investigation (How did you isolate it?):**  
   *"I traced the worker logs and discovered an 11-second asynchronous race condition. Our Hugging Face embedding client was stalling on a DNS lookup timeout in Docker, but our matching endpoint was executing immediately and querying `WHERE self_embedding IS NOT NULL` before vectors were persisted."*
3. **The Engineering Fix (What did you implement?):**  
   *"I solved it in two ways: first, I replaced static sleep timers with active readiness polling on `embedding_source_text` in the database. Second, I lowered the external API timeout to 3 seconds and implemented a fast, offline deterministic embedding fallback so the worker never stalls."*
4. **The Takeaway / Architectural Insight:**  
   *"This reinforced the importance of building resilient state-polling mechanisms in asynchronous event-driven pipelines rather than relying on timing assumptions."*

