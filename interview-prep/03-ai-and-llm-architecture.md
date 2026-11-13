# 03. AI & LLM Architecture

> **Engineering Production AI at Belong**  
> *LangGraph state machines, psychometric signal extraction, dual-space embeddings, anti-hallucination prompting, and two-stage candidate reasoning.*

---

## 1. LangGraph Fundamentals in Belong

### What is LangGraph & Why Not Simple Chains?
Most early LLM apps use basic linear pipelines (`Prompt -> LLM -> OutputParser`). This breaks down quickly in multi-turn conversational agents because:
1. **Conversations are state machines:** A turn depends on previous turns, covered topics, follow-up counts, and extracted attributes.
2. **Dynamic Branching & Cycles:** You need conditional edges: *"Did the user answer with sufficient depth? If no, loop back and probe. If yes, advance to next topic. If all topics complete, check if high-priority psychological traits are missing."*
3. **State Persistence:** The state must be serializable to a database (`PostgreSQL`) between HTTP turns and reloaded on the next message.

### Core LangGraph Concepts Applied in Belong:
* **State (`TypedDict`):** The shared memory contract passed between all graph nodes.
* **Nodes:** Python functions (`async def`) that accept the state, execute business logic or LLM calls, and return a dictionary of state updates.
* **Edges:** Determine the next node to transition to.
* **Compilation:** `workflow.compile()` creates an immutable, executable graph instance (`CompiledStateGraph`).

---

## 2. Belong's Onboarding StateGraph Implementation

The conversational onboarding engine in `belong-api/onboarding/graph.py` is structured as a two-node turn-based graph:

```
                      +-----------------------------+
                      |      Incoming HTTP Turn     |
                      |  (User Message + Prev State)|
                      +--------------+--------------+
                                     |
                                     v
                      +-----------------------------+
                      |   NODE 1: extract_signals   |
                      | - LLM Extraction Prompt     |
                      | - JSON Parsing & Regex Fix  |
                      | - Confidence Filter (>=0.50)|
                      | - Quote Verification (<=80c)|
                      | - Deduplication & ID Gen    |
                      +--------------+--------------+
                                     |
                                     | Normal Edge
                                     v
                      +-----------------------------+
                      |  NODE 2: generate_response  |
                      | - Vagueness Check (LLM)     |
                      | - Follow-up Cap Check (<=2) |
                      | - Advance or Probe Decision |
                      | - Post-Core Coverage Check  |
                      | - Warm Chatbot Reply Gen    |
                      +--------------+--------------+
                                     |
                                     | Transitions to END
                                     v
                      +-----------------------------+
                      |             END             |
                      | If completed:               |
                      |   finalize_profile()        |
                      |   Enqueue Embedding Job     |
                      +-----------------------------+
```

### The State Contract: `OnboardingState`
Defined in `belong-api/onboarding/state.py`:
```python
class OnboardingState(TypedDict, total=False):
    conversation_id: str
    user_id: str
    covered_areas: List[str]            # Topics successfully completed (e.g. ['q1_intent', 'q2_values'])
    current_area_index: int            # Index of active core question (0 to len(questions)-1)
    follow_up_count: int               # Cumulative follow-up counter across session (Capped at 2)
    extracted_signals: Dict[str, Any]  # Accumulated psychometric signals (self.*, wants.*, constraints.*)
    latest_user_input: Optional[str]   # Raw string message received from user this turn
    latest_assistant_response: Optional[str] # Final warm reply generated for user
    active_probe_field: Optional[str]  # Field currently being targeted by adaptive probe
    active_probe_prompt: Optional[str] # Prompt text of targeted probe
    status: str                        # 'active' or 'completed'
```

---

## 3. Node Deep Dive: How the Onboarding Graph Executes

### Node 1: `extract_signals_node`
Executes on **every user reply** before determining the next question:
1. **Prompt Assembly:** Combines the system prompt (`SIGNAL_EXTRACTION_PROMPT`), the current question topic, and the raw user message.
2. **Extraction Payload:** The LLM is instructed to act as a structured psychometric parser and emit JSON:
   ```json
   {
     "extracted_items": [
       {
         "target_field": "self.values",
         "label": "Values emotional honesty",
         "summary": "Values transparent and vulnerable emotional honesty in partners.",
         "quote": "I can't stand when people hide how they really feel.",
         "confidence": 0.95,
         "evidence_type": "explicit"
       }
     ],
     "novel_signals": []
   }
   ```
3. **Clinical Quality Filters (Engineering Rigor):**
   * **Confidence Threshold:** Any item with `confidence < 0.50` is discarded immediately.
   * **Quote Grounding:** Quotes are truncated to max 80 characters to keep citations punchy and prevent users' entire paragraphs from polluting signal summaries.
   * **Deduplication:** Compares clean label and quote substrings against existing signals in `extracted_signals[field_path]`. Duplicate traits are discarded.
   * **Deterministic Signal IDs:** Formats signal IDs predictably:  
     `{topic_id}_{field_abbrev}_{index}` (e.g., `q1_intent_s_values_00`).
   * **Novel Signals Handling:** Uncategorized insights that don't fit the standard schema are captured under `novel_signals` rather than thrown away.

---

### Node 2: `generate_response_node` (Adaptive Logic & Probing)

This node governs conversational flow, adaptive probing, and session termination:

```
                         generate_response_node
                                   |
         +-------------------------+-------------------------+
         |                                                   |
   Core Questions Remain                               All Core Finished
         |                                                   |
   Vagueness Check                                    Coverage Check:
   (Is reply shallow?)                                Missing HIGH_PRIORITY_FIELDS?
   +-----+-----+                                      +-----+-----+
   |           |                                      |           |
 Vague       Solid                                  Missing    All Covered
(count < 2)    |                                  (count < 2)     |
   |           v                                      |           v
   |       Advance idx + 1                            |       Status = 'completed'
   v       Covered_areas.append                       v       finalize_profile()
 Generate Probe                                  Generate     Enqueue Embedding
 count += 1                                      Adaptive     Warm Conclusion
 Status = 'active'                               Probe
                                                 count += 1
```

#### Key Invariants & Safeguards:
1. **The Follow-Up Invariant (`MAX_FOLLOW_UPS = 2`):**
   * Real users abandon onboarding if the bot interrogates them endlessly. Belong enforces a **strict session cap of 2 follow-ups max**.
   * Validated in code via assertion: `assert follow_up_count <= MAX_FOLLOWUPS`.
2. **Vagueness Detection (`VAGUENESS_CHECK_PROMPT`):**
   * The LLM checks if the user's answer was superficial (e.g., *"idk, just normal stuff"* or *"good vibes"*).
   * If vague and `follow_up_count < 2`, the system triggers an empathetic follow-up to unpack the response.
3. **High-Priority Coverage Detection:**
   * Critical relationship fields:
     * `self.provides` (*"What do you naturally do for a partner when they are having a hard time?"*)
     * `self.emotional_needs` (*"When stressed, what helps you feel supported?"*)
     * `self.conflict_style` (*"How do you handle disagreement or tension?"*)
   * If a user finishes the scripted questions without ever mentioning conflict or emotional support, `find_missing_high_priority_field()` identifies the blind spot and generates an adaptive probe.

---

## 4. Dual-Aspect Representation: `SELF` vs. `WANTS`

Why does Belong separate `SELF` and `WANTS` instead of creating one single profile summary?

### The "Opposites vs. Similars" Trap
Traditional matching systems make the fatal assumption that **similarity equals compatibility**.
* If User A is an anxious communicator who needs explicit verbal validation, matching them with another anxious communicator who withdraws under stress causes disaster.
* They actually need a **complementary** partner: someone whose `provides` is grounded, patient, and communicative.

```
+------------------------------------+------------------------------------+
|            USER A (Self)           |           USER B (Wants)           |
+------------------------------------+------------------------------------+
| "I am quiet, observant, and take   | "Looking for a thoughtful, calm    |
|  time to open up. I show care by   |  partner who shows love through    |
|  acts of service."                 |  actions rather than loud words."  |
+------------------------------------+------------------------------------+
                                  MATCH!
```

### Profile Data Model (`StructuredProfileJSON`)
Implemented with Pydantic in `belong-api/profile/models.py`:
* **`self`**:
  * `values`: Fundamental ethics, family views, spiritual orientation.
  * `provides`: Emotional support offered, caretaking habits, active listening.
  * `emotional_needs`: Reassurance mechanisms, distress preferences.
  * `conflict_style`: De-escalation, time-out preferences, direct discussion.
  * `lifestyle`: Work-life balance, morning/night rhythm, social battery.
* **`wants`**:
  * `partner_traits`: Desired personality traits (patient, ambitious, warm).
  * `partner_values`: Shared foundational philosophies.
  * `relationship_expectations`: Monogamy, timeline, marriage, cohabitation.
* **`constraints`**:
  * `dealbreakers`: Hard limits (e.g., non-smoker, location, children).

---

## 5. Embeddings & Canonical Semantic Serialization

### Why You Cannot Directly Embed Raw Profile JSON
If you pass raw JSON to an embedding model:
```json
{"self": {"values": [{"label": "Honesty", "confidence": 0.95, "id": "q1_val_00"}]}}
```
1. **Structural Noise:** The vector model expends its finite dimensionality encoding syntax characters (`{`, `[`, `"confidence"`, `0.95`).
2. **Diluted Attention:** Long boilerplate reduces the semantic weight of the actual psychological meaning.

### The Canonical Serializer Solution (`CanonicalSerializer`)
Located in `belong-api/embeddings/serializer.py`:
1. Discards low-confidence items ($< 0.50$).
2. Strips quotes, timestamps, question IDs, and field keys.
3. Formats traits into clean, natural-language, section-based text blocks:

```text
SELF
Values: Values transparent honesty, Values personal growth and ambition.
Provides: Practical support in distress, Pays attention to details.
Emotional needs: Needs explicit verbal reassurance when stressed.
Conflict style: Prefers taking space before resolving heated arguments.
```

```text
WANTS
Partner traits: Grounded, patient listener, Emotionally expressive.
Relationship expectations: Long-term partnership leading to marriage.
```

### The Embedding Model: `all-MiniLM-L6-v2`
* **Architecture:** BERT-based sentence transformer.
* **Output Dimension:** **384 dense floats**.
* **Why this model?**
  * **Ultra-Fast Inference:** ~15ms per text string on CPU.
  * **Compact Storage:** 384 dimensions require only $384 \times 4 \text{ bytes} \approx 1.5 \text{ KB}$ per vector in Postgres. Compared to OpenAI `text-embedding-3-large` (3072 dimensions $\approx 12.2 \text{ KB}$), MiniLM offers a **$8\times$ reduction in index memory footprint**.
  * **High Semantic Density:** Excellent performance on semantic textual similarity (STS) benchmarks.
* **Non-Blocking Async Execution (`EmbeddingClient`):**
  PyTorch encoding is CPU-bound. Calling it directly in an async function would block the entire Python event loop. Belong runs it in a background thread executor:
  ```python
  embeddings = await loop.run_in_executor(
      None, lambda: model.encode(cleaned_texts, convert_to_numpy=True).tolist()
  )
  ```

---

## 6. Cosine Similarity vs. Cosine Distance in `pgvector`

In `pgvector`, the `<=>` operator computes **Cosine Distance**:
$$\text{Cosine Distance}(A, B) = 1.0 - \frac{A \cdot B}{\|A\|_2 \|B\|_2}$$

* If two vectors point in the identical direction: Cosine Distance $= 0.0$ (Cosine Similarity $= 1.0$).
* If two vectors are orthogonal ($90^\circ$): Cosine Distance $= 1.0$ (Cosine Similarity $= 0.0$).
* If two vectors are opposite ($180^\circ$): Cosine Distance $= 2.0$ (Cosine Similarity $= -1.0$).

### Belong's Bidirectional Scoring Formula:
$$\text{Forward Similarity} = 1.0 - \big(\text{Candidate } self\_embedding \;\Longleftrightarrow\; \text{User A } wants\_embedding\big)$$
$$\text{Reverse Similarity} = 1.0 - \big(\text{Candidate } wants\_embedding \;\Longleftrightarrow\; \text{User A } self\_embedding\big)$$
$$\text{Combined Score} = 0.5 \times \text{Forward Similarity} + 0.5 \times \text{Reverse Similarity}$$

This ensures that candidates who want what User A provides, and provide what User A wants, bubble to the top.

---

## 7. Stage 1 Retrieval vs. Stage 2 LLM Reasoning

Why have two stages? Why not use LLM for everything, or vector search for everything?

```
+---------------------------------------+---------------------------------------+
|   STAGE 1: pgvector & SQL Recall      |     STAGE 2: Pairwise LLM Reasoning   |
+---------------------------------------+---------------------------------------+
| Candidates: 10,000+ -> 15             | Candidates: 15 -> Ranked Matches      |
| Latency: ~5 - 20 ms                   | Latency: ~10 - 20 seconds             |
| Cost: $0.00 (In-database compute)     | Cost: ~$0.01 per batch                |
| Nature: Coarse quantitative filter    | Nature: Deep qualitative analysis     |
| Answers: "Do their broad traits align | Answers: "HOW will they resolve       |
| and do they meet basic constraints?"  | conflicts? Do their attachment styles |
|                                       | clash? Are dealbreakers violated?"    |
+---------------------------------------+---------------------------------------+
```

---

## 8. Stage 2 Pairwise Reasoning: LangGraph & Anti-Hallucination

In `belong-workers/matching/compatibility.py`, Belong uses a dedicated LangGraph workflow to evaluate pairs:

```
                  ┌─────────────────────────────────────────────────────────┐
                  │                 PAIRWISE INPUT STATE                    │
                  │  - user_a_profile (Alice's raw extracted profile)       │
                  │  - user_b_profile (Bob's raw extracted profile)         │
                  └────────────────────────────┬────────────────────────────┘
                                               │
                                               ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ NODE 1: format_prompt_node                                                                  │
│                                                                                             │
│ 1. Profile Slimming (_slim_profile):                                                        │
│    - Strips internal IDs, timestamps, question IDs, and confidence floats.                  │
│    - Keeps only: label, summary, quote, demographics (age, gender, goal).                   │
│    - RESULT: Cuts prompt token count by ~50% (saves API costs, avoids Groq rate limits).    │
│                                                                                             │
│ 2. Formats PAIRWISE_REASONING_PROMPT_TEMPLATE:                                              │
│    - Injects slimmed JSON strings for User A and User B.                                    │
│    - Writes output string into state["prompt_text"].                                        │
└──────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                               │
                                               │ (Normal Edge)
                                               ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│ NODE 2: llm_reasoning_node                                                                  │
│                                                                                             │
│ 1. Invokes Groq LLM (LLaMA-3.3-70B) with strict system instructions:                        │
│    "Return JSON ONLY. Start with '{' and end with '}'."                                     │
│                                                                                             │
│ 2. Evaluates the 4 core relationship dimensions:                                            │
│    - Emotional Needs                                                                        │
│    - Core Values                                                                            │
│    - Lifestyle                                                                              │
│    - Conflict Style                                                                         │
│                                                                                             │
│ 3. Enforces Anti-Hallucination & Quotes:                                                    │
│    - Must cite verbatim quotes from both User A and User B.                                 │
│    - If unmentioned, dimension verdict MUST be "unclear" (NO guessing).                     │
│                                                                                             │
│ 4. Parses and validates against Pydantic schema:                                            │
│    PairwiseCompatibilityOutput -> writes to state["parsed_output"].                         │
└──────────────────────────────────────────────┬──────────────────────────────────────────────┘
                                               │
                                               │ (Transitions to END)
                                               ▼
                                   ┌──────────────────────┐
                                   │         END          │
                                   │  Returns evaluation  │
                                   └──────────────────────┘
```

### Profile Slimming & Prompt Safeguards:
1. **Profile Slimming (`_slim_profile`):**
   Before sending profiles to the reasoning LLM, all debugging metadata is removed:
   * Keeps: `label`, `summary`, `quote`, demographics (`age`, `gender`, `goal`).
   * Drops: internal UUIDs, question IDs, timestamps, confidence scores.
   * **Result:** Cuts prompt token consumption by **~50%**, keeping Groq requests well within rate limits and drastically reducing TTFT (time-to-first-token).
2. **Pairwise Prompt Constraints:**
   The prompt instructs the model:
   * *"Evaluate compatibility across 4 dimensions: Emotional Needs, Core Values, Lifestyle, and Conflict Style."*
   * *"For every claim, cite explicit, verbatim quotes from User A and User B."*
   * *"If User A or B did not mention a trait, classify that dimension as 'unclear'—NEVER hallucinate assumptions."*
3. **Structured Output Enforcement (`PairwiseCompatibilityOutput`):**
   Validated via Pydantic:
   * `overall_verdict`: Enum (`strong_alignment`, `partial_alignment`, `unclear`, `conflict`).
   * `reciprocity_score`: Float between 0.0 and 1.0.
   * `dimension_results`: Detailed evidence quotes for each of the 4 dimensions.
   * `dealbreaker_violations`: Explicit list of any hard limits violated.

---

## 9. Handling Invalid, Inconsistent, or Malformed LLM Outputs

Production AI engineering requires defensive handling of unpredictable model outputs:

| Failure Mode | How Belong Solves It in Code |
| :--- | :--- |
| **Markdown Fences** (LLM outputs ````json ... ````) | Code automatically splits on ```` ```json ```` and extracts inner string content. |
| **Preamble Text** (*"Sure, here is your JSON:"*) | Regex fallback: `re.search(r"\{[\s\S]*\}", content)` finds the outermost JSON object brackets. |
| **Empty Content Response** | Detected immediately via `hasattr(res, 'content') and not res.content`. Triggers retry. |
| **Rate Limits (HTTP 429) & Connection Glitches** | Custom retry decorator `_retry_llm_invoke` executes up to 3 attempts with **exponential backoff** ($2^0, 2^1, 2^2 \text{ seconds}$). |
| **Schema Validation Error** | Caught in `try/except`. Logs error for the specific candidate and continues evaluating remaining candidates in the batch without crashing the worker. |

