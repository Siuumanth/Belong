# Onboarding Graph & Session Workflow

This document details the LangGraph state machine, HTTP lifecycle, and persistence architecture powering the conversational onboarding in Belong (`belong-api/onboarding/graph.py`).

---

## 1. Request-Response Lifecycle Sequence

The conversational onboarding uses a **stateless, turn-by-turn request model**. Instead of maintaining persistent background loops or long-lived server memory, every user message triggers an atomic execution of the LangGraph state machine.

```mermaid
sequenceDiagram
    autonumber

    actor User as User / Client
    participant API as FastAPI (routes/onboarding.py)
    participant DB as PostgreSQL (conversations, messages)
    participant Graph as LangGraph Engine (graph.py)
    participant LLM as Groq / Llama-3.3-70B
    participant MQ as RabbitMQ (belong.embedding)

    User->>API: POST /api/onboarding/message<br/>{conversation_id, message}
    API->>DB: Fetch conversation progress and extracted_signals
    API->>DB: INSERT conversation_messages<br/>(role = user)
    API->>Graph: onboarding_graph.ainvoke(current_state)

    rect rgb(240, 245, 255)
        Note over Graph,LLM: Step 1: extract_signals_node

        Graph->>LLM: Prompt with question_text, target_dimensions and user input
        LLM-->>Graph: JSON with atomic signals<br/>(label, summary, quote, confidence)
        Graph->>Graph: Merge signals into state
        Graph->>Graph: Clear active probe
    end

    rect rgb(245, 255, 240)
        Note over Graph,LLM: Step 2: generate_response_node

        Graph->>Graph: Check coverage against freshly merged signals

        alt Core questions active and answer is vague
            Graph->>LLM: Vagueness check prompt
            LLM-->>Graph: needs_follow_up = true
            Graph->>Graph: Increment follow_up_count<br/>(maximum 2)

        else Core questions complete (current_idx >= 6)

            alt Missing high-priority field and follow_up_count < 2
                Graph->>Graph: Select missing field
                Graph->>Graph: Generate targeted behavioral probe
                Graph->>Graph: Increment follow_up_count
                Graph->>Graph: Mark probe field in covered_areas

            else Coverage passed or follow_up_count >= 2
                Graph->>Graph: Mark status = completed
                Graph->>DB: finalize_profile()<br/>Write atomic profile to profiles
            end
        end

        Graph->>LLM: Generate warm acknowledgment and next prompt
        LLM-->>Graph: Chatbot reply string
    end

    Graph-->>API: new_state<br/>(status, extracted_signals, assistant_response, ...)
    API->>DB: INSERT conversation_messages<br/>(role = assistant)
    API->>DB: UPDATE conversations state and status

    opt Status is completed
        API->>DB: Create embedding job<br/>(type = embedding, status = pending)
        API->>MQ: Publish job to belong.embedding
    end

    API-->>User: HTTP 200<br/>{assistant_response, status, follow_up_count}
```

### Explanation of Diagram 1
1. **Stateless Reconstitution**: FastAPI reads the user's progress (`current_area_index`, `follow_up_count`, `covered_areas`, and `extracted_signals`) directly from PostgreSQL.
2. **Two-Node Graph Invocation**:
   - `extract_signals_node`: Extracts atomic traits with verbatim user quotes and confidence scores $\ge 0.50$.
   - `generate_response_node`: Re-evaluates profile completeness, checks answer depth, manages follow-up counts, and drafts the next question.
3. **Atomic Finalization**: When onboarding completes, the graph calls `finalize_profile()` to compile signals into the `profiles` table and enqueues an asynchronous vector embedding job via RabbitMQ.

---

## 2. LangGraph State Machine & Coverage Logic

The internal decision flow of the LangGraph state machine enforces strict termination invariants and adaptive probing.

```mermaid
flowchart TD
    Start([User Answer Received]) --> Node1["Node 1: extract_signals_node<br/>• Reads user input + active question text<br/>• Maps behavioral partner support to self.provides<br/>• Filters confidence < 0.50<br/>• Merges atomic signals into state"]
    
    Node1 --> Node2["Node 2: generate_response_node<br/>Check state progress: current_area_index"]
    
    Node2 --> CheckIndex{"Is current_area_index < len(questions)?<br/>(Core Questions 1 to 6)"}
    
    CheckIndex -- "Yes (Core Active)" --> CheckVague{"Answer vague AND<br/>follow_up_count < MAX_FOLLOWUPS (2)?"}
    
    CheckVague -- "Yes" --> AskInTopic["Generate In-Topic Probe<br/>• follow_up_count += 1<br/>• Keep current_area_index<br/>• status = 'active'"]
    
    CheckVague -- "No" --> AdvanceCore["Advance Core Index<br/>• covered_areas.append(q.id)<br/>• current_area_index += 1"]
    
    AdvanceCore --> Recheck{"Is current_area_index < 6?"}
    Recheck -- "Yes" --> NextCore["Ask Next Core Question<br/>• status = 'active'"]
    Recheck -- "No" --> PostCoreCheck
    
    CheckIndex -- "No (Post-Core Index >= 6)" --> PostCoreCheck{"Check Profile Coverage<br/>find_missing_high_priority_field()"}
    
    PostCoreCheck -- "Missing field AND<br/>follow_up_count < 2 AND<br/>NOT already probed" --> AskProbe["Ask Adaptive Behavioral Probe<br/>• e.g. self.provides behavioral support<br/>• covered_areas.append('probe:self.provides')<br/>• follow_up_count += 1<br/>• status = 'active'"]
    
    PostCoreCheck -- "Coverage passed OR<br/>follow_up_count >= MAX_FOLLOWUPS (2)" --> Complete["Finalize Onboarding<br/>• status = 'completed'<br/>• finalize_profile() writes atomic signals to profiles<br/>• Enqueue background embedding job"]
    
    AskInTopic --> ReturnState([Return State to API & Persist to DB])
    NextCore --> ReturnState
    AskProbe --> ReturnState
    Complete --> ReturnState
```

### Explanation of Diagram 2
- **Core Question Traversal**: The user progresses sequentially through 6 core dimensions (`q1_values` through `q6_conflict`).
- **In-Topic Follow-Ups**: If an answer is too brief or evasive during core questions, the graph asks an in-topic follow-up without advancing the index (up to `MAX_FOLLOWUPS = 2`).
- **Post-Core Adaptive Probing**: Once core questions finish, if critical dimensions (like `self.provides`) lack sufficient evidence, the graph asks a concrete behavioral probe.
- **Duplicate Probe Guard**: Once a dimension probe is asked (tagged `probe:{field}` in `covered_areas`), it is permanently suppressed from being asked again.
- **Hard Cap Termination**: If `follow_up_count >= 2`, onboarding unconditionally marks `status = 'completed'` and finalizes the profile.

---

## 3. Developer Notes & Invariant Rules

### Invariant 1: Total Turn Upper Bound
```text
6 core questions + at most 2 follow-ups = maximum 8 user turns.
Never Q9 or Q10.
```

### Invariant 2: Hard Follow-Up Cap
In `belong-api/onboarding/graph.py`:
```python
MAX_FOLLOWUPS = settings.MAX_FOLLOW_UPS  # Value: 2
# Checked before any follow-up probe or in-topic question is scheduled
```

### Invariant 3: Duplicate Probe Guard
Adaptive probes are tagged with `probe:{field}` inside `covered_areas`. If a user cannot provide a field, it is marked as probed and the graph either moves to the next missing dimension or completes. It will never loop on the same question.

### Invariant 4: Atomic Evidence Signals
Every extracted signal adheres to this strict atomic structure:
```json
{
  "id": "q4_lifestyle_values_s_lifestyle_00",
  "label": "Enjoys trail running",
  "summary": "The user enjoys trail running.",
  "quote": "Trail running",
  "question_id": "q4_lifestyle_values",
  "confidence": 0.98,
  "evidence_type": "explicit"
}
```
* **Verbatim Quotes**: The `quote` field is strictly excerpted from the user's text.
* **No Placeholders**: Generic text like `"evidence": "survey response"` is strictly rejected.
* **Confidence Floor**: Signals with confidence below `0.50` are automatically pruned.
