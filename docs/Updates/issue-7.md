# Issue 7: Empty Compatibility Results & Pairwise LLM Matching Pipeline Failure

**Date:** 2026-09-30  
**Status:** Resolved & Verified  
**Affected Service(s):** `belong-workers` (MatchingWorker, EmbeddingWorker), `belong-api`  

---

## 1. Executive Summary

During full simulation runs, user demographic profiles, multi-turn onboarding dialogues, and trait extraction succeeded with high fidelity ($0.95 - 0.99$ confidence). However, **`compatibility_results` remained completely empty (0 rows)** and match runs concluded with `candidate_count: 0`.

Investigation revealed two compound root causes:
1. **Asynchronous Vector Race Condition:** The test runner triggered matching while background vector embedding generation was still pending, causing Stage 1 candidate recall to find 0 candidates.
2. **Groq Structured Output Token Truncation (`tool_use_failed`) & Rate Limit Crash:** In cases where candidates were recalled, the LLM reasoning step exceeded token limits, truncated JSON output, triggered Groq tool failure, and crashed on an empty fallback response.

Both root causes were resolved, and pairwise compatibility reasoning with reciprocal alignments now successfully persists to PostgreSQL.

---

## 2. Root Cause Analysis

### Problem A: 11-Second Asynchronous Race Condition

#### The Mechanism:
In `tests/run_custom_simulation.py`, the test queued vector embedding generation jobs for User A and User B and executed a static `await asyncio.sleep(5)`.

In the background, `EmbeddingWorker` in `belong-workers` made requests to the HuggingFace Feature Extraction endpoint. Due to container DNS / network delays (`Temporary failure in name resolution`), the client stalled for 16 seconds before falling back to local deterministic hash vectors.

#### The Failure Chain:
```text
16:32:54 - Embedding jobs queued for User A and User B
16:32:59 - [5s elapsed] Test immediately fires POST /api/matches
16:32:59 - Stage 1 Recall runs: SELECT ... WHERE p.self_embedding IS NOT NULL
           --> Neither profile had embeddings written to Postgres yet!
           --> Stage 1 recalled 0 candidates.
16:32:59 - MatchingWorker logs: "No eligible candidate matches found". Match run completes with 0 results.
16:33:10 - [11s later!] EmbeddingWorker finally finishes writing vectors to Postgres.
```

Because matching completed before embeddings were persisted, the pipeline never reached Stage 2 qualitative reasoning.

---

### Problem B: Pairwise LLM Reasoning Crash (`tool_use_failed` & `JSONDecodeError`)

#### The Mechanism:
When Stage 1 candidate recall did find a match, `PairwiseCompatibilityAgent` evaluated User A and User B using `ChatGroq` (`openai/gpt-oss-120b`).

1. **Token Truncation:**
   The output schema `PairwiseCompatibilityOutput` (4 dimensions, evidence IDs, citations, reciprocal fulfillment, shared alignments, and narrative summaries) is token-intensive. With `max_tokens` set to `2048`, the model truncated mid-generation:
   ```json
   "emotional_needs": {
     "evidence_a_ids": [
       "q2_emotional_needs_s_emotional_needs_00",
       "q2_emotional_ne
   ```
2. **Groq 400 Bad Request:**
   Groq's tool calling runtime could not parse the truncated arguments and failed with:
   `Error code: 400 - {'error': {'message': 'Failed to parse tool call arguments as JSON', 'code': 'tool_use_failed'}}`
3. **Cascading 429 & Empty Output Crash:**
   The fallback handler attempted an immediate second plain LLM invoke. This second request triggered Groq's rate limit:
   `HTTP 429 Too Many Requests (Retrying in 19.0s)`.
   After the 19-second delay, the API returned an HTTP 200 with an empty body (`content = ""`).
   Executing `json.loads("")` raised:
   `json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)`
4. **Abortion:**
   The unhandled exception aborted pairwise evaluation, causing the worker to log `Persisted 0 compatibility results`.

---

## 3. Implemented Fixes

### Fix 1: Resilient LLM Recovery & Increased Token Ceiling
**File:** [`belong-workers/matching/compatibility.py`](file:///d:/code/Golang/Belong/belong-workers/matching/compatibility.py)

1. **Increased Token Limit:** Raised `max_tokens` from `2048` to `4096` in `get_llm()` for Groq models to ensure complete schema generation.
2. **`failed_generation` Direct Extraction:**
   When Groq raises a `400 tool_use_failed`, it embeds the generated JSON arguments in the error string (`failed_generation`). The recovery logic now extracts this payload using regex and parses it directly, eliminating unnecessary secondary API calls and avoiding the subsequent 429 rate limit.
3. **Empty-Response Guard in Retry Loop:**
   Updated `_retry_llm_invoke()` to inspect response content and retry if the API returns an empty body string.
4. **Verdict Fallbacks:**
   Added default normalization for `overall_verdict` to prevent validation errors if the verdict field is omitted in partial model generations.

---

### Fix 2: Fast Embedding Fallback & Active Vector Polling
**Files:** [`belong-workers/embeddings/client.py`](file:///d:/code/Golang/Belong/belong-workers/embeddings/client.py), [`tests/run_custom_simulation.py`](file:///d:/code/Golang/Belong/tests/run_custom_simulation.py)

1. **Reduced HTTP Timeout:** Lowered the HuggingFace API timeout in `EmbeddingClient` from `30.0s` to `3.0s` and set `wait_for_model=False`. If offline, deterministic fallback embeddings generate within 50ms rather than hanging for 15+ seconds.
2. **Active Readiness Polling:** Replaced the static `sleep(5)` in `run_custom_simulation.py` with an active polling loop that checks the user profile endpoint until `embedding_source_text` is confirmed written to PostgreSQL before initiating matching.

---

### Fix 3: Standalone Match Trigger Tooling
**File:** [`tests/trigger_matching_only.py`](file:///d:/code/Golang/Belong/tests/trigger_matching_only.py)

Created a dedicated script to test matching on existing database profiles without re-running the multi-turn onboarding simulation:
- Discovers existing candidate pairs in PostgreSQL.
- Posts `POST /api/matches` with proper `X-User-ID` headers.
- Polls the background match job to completion.
- Inspects and verifies the newly created rows in `compatibility_results`.

---

## 4. Verification & Results

### Execution Output (`tests/trigger_matching_only.py`):
```text
Match Run ID   : a2cbaf9d-a661-4301-a11b-16a4d6af57b2
User A ID      : 05ab5210-9061-427a-a590-7707065aa072 (Bob)
User B ID      : 936d28d2-6349-478d-b6fb-4e146b182b51 (Alice)
Status         : completed
Candidate Count: 1
```

### Persisted Record in `compatibility_results`:
- **Match Record ID:** `bc5887aa-bd04-495c-bed9-569692bc81c9`
- **Overall Compatibility Reasoning:**
  > *"The pair shows strong reciprocal emotional support—A’s patient listening meets B’s need for presence, and B’s frequent check‑ins and reassurance satisfy A’s need for reassurance. They share core values of honesty and a desire for long‑term growth, though their conflict styles differ slightly (quick resolution vs. cooldown). Overall, the compatibility is promising but not flawless, leading to a partial alignment verdict."*
- **Reciprocal Alignments (Complementary Fulfillment):**
  - `A wants reassurance & respect -> B provides frequent check‑ins (q3_conflict_provides_s_provides_01)`
  - `A wants reassurance & respect -> B shows up emotionally (q5_personality_s_provides_06)`
  - `B wants emotional presence & regular check‑ins -> A provides patient listening & reassurance (probe_provides_s_provides_00)`
  - `B wants verbal reassurance -> A provides patient listening & reassurance (probe_provides_s_provides_00)`
  - `B wants good communication -> A provides patient listening (probe_provides_s_provides_00)`
- **Dimension Verdicts:**
  - `lifestyle`: `strong_alignment`
  - `emotional_needs`: `strong_alignment`
  - `core_values`: `partial_alignment`
  - `conflict_style`: `partial_alignment`
- **Dealbreaker Violations:** `[]`
