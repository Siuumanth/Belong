# Stage 2 Pairwise Reciprocal Reasoning LangGraph & Worker Workflow

This document details the Stage 2 Pairwise Reasoning workflow executed by `PairwiseCompatibilityAgent` in [`belong-workers/matching/compatibility.py`](file:///d:/code/Golang/Belong/belong-workers/matching/compatibility.py) and [`belong-workers/workers/matching_worker.py`](file:///d:/code/Golang/Belong/belong-workers/workers/matching_worker.py).

---

## 1. LangGraph State Machine Architecture

Stage 2 executes a compiled 3-node LangGraph state machine for each candidate retrieved from Stage 1.

```mermaid
flowchart TD
    Start([Pair Input: User A & User B Profiles]) --> Node1["Node 1: format_prompt<br/>• Injects User A & B structured JSON into prompt template<br/>• Sets up reciprocal reasoning rules (wants <-> provides)<br/>• Outputs prompt_text in state"]
    
    Node1 --> Node2["Node 2: llm_reasoning<br/>• Calls Groq Llama-3.3-70B<br/>• Enforces Pydantic schema: PairwiseCompatibilityOutput<br/>• Evaluates dimensions, reciprocal alignments, conflicts"]
    
    Node2 --> CheckLLM{"LLM Execution Success?"}
    
    CheckLLM -- "No (Error)" --> RecordErr["Record error in state<br/>parsed_output = None"]
    CheckLLM -- "Yes" --> Node3["Node 3: validation<br/>• Normalizes verdicts to valid set<br/>• _build_signal_index(): indexes {signal_id: quote}<br/>• Resolves evidence IDs -> actual user quotes<br/>• Attaches resolved_evidence to state"]
    
    RecordErr --> EndState([Return State & Log Error])
    Node3 --> EndGraph([CompiledStateGraph.END])
    EndGraph --> Persist["MatchingWorker Persists to DB<br/>• INSERT into compatibility_results<br/>• complementary_alignments<br/>• shared_alignments<br/>• dimension_results, conflicts, dealbreakers"]
```

### Explanation of Diagram 1
1. **`format_prompt`**: Formats the prompt using `PAIRWISE_REASONING_PROMPT_TEMPLATE`, embedding the structured `self`, `wants`, and `constraints` of both individuals.
2. **`llm_reasoning`**: Groq's `llama-3.3-70b-versatile` generates structured compatibility analysis via `with_structured_output(PairwiseCompatibilityOutput)`.
3. **`validation`**:
   - Ensures the overall verdict matches `{"strong_alignment", "partial_alignment", "unclear", "conflict"}`.
   - Builds a flat lookup index mapping signal IDs to user quotes (`_build_signal_index`), verifying citations.
4. **Database Persistence**: Upserts the evaluated compatibility into the `compatibility_results` table in PostgreSQL.

---

## 2. Reciprocal Alignment vs. Shared Alignment Model

A core architectural principle in Belong is the strict distinction between **complementary reciprocity** and **shared similarity**.

```mermaid
flowchart LR
    subgraph Reciprocal ["Complementary Alignments (Dynamic Fit)"]
        direction TB
        A_wants["User A Wants<br/>'Needs words of affirmation'"] <--> B_provides["User B Provides<br/>'Actively gives reassurance'"]
        B_wants["User B Wants<br/>'Desires calm partner'"] <--> A_provides["User A Provides<br/>'Grounded conflict demeanor'"]
    end

    subgraph Shared ["Shared Alignments (Similarity)"]
        direction TB
        A_values["User A Values<br/>'Outdoor lifestyle, vegan'"] <--> B_values["User B Values<br/>'Enjoys hiking, vegetarian'"]
        A_goals["User A Life Goals<br/>'Settling down within 2 yrs'"] <--> B_goals["User B Life Goals<br/>'Wants long-term family'"]
    end
```

### Explanation of Diagram 2
- **Complementary Alignments (`complementary_alignments`)**: Captures reciprocal fulfillment: what Person A specifically asks for must be actively provided by Person B, and vice-versa ($A.\text{wants} \leftrightarrow B.\text{self.provides}$).
- **Shared Alignments (`shared_alignments`)**: Captures commonality: shared interests, mutual worldviews, and synchronized timeline goals ($A.\text{self.values} \leftrightarrow B.\text{self.values}$).
- These two arrays are stored as separate JSONB columns in `compatibility_results` and returned distinctly by the Match API.

---

## 3. Developer Notes & Anti-Over-Inference Invariants

### 1. Anti-Over-Inference Rules
The reasoning prompt enforces strict logical discipline:
* **"Calm / Thoughtful" $\neq$ "Active Listening"**: A candidate being quiet or introspective cannot be cited as evidence of "active listening" unless they explicitly stated they listen attentively.
* **"Empathetic" $\neq$ "Reassurance"**: Being warm or compassionate is not proof that someone provides verbal reassurance during anxiety.
* **Unclear over Hallucination**: If evidence is missing for a partner's need, the LLM must classify the alignment as `uncertainties` rather than assuming it exists.

### 2. Evidence Traceability
Every claim in `dimension_results` cites atomic IDs (`evidence_a_ids`, `evidence_b_ids`). The `validation_node` indexes every signal from both profiles and resolves these citations into verbatim quotes, ensuring every match explanation is fully auditable.
