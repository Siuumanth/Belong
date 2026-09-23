# Onboarding Graph & Persistence Architecture

The conversational onboarding in Belong combines **durable PostgreSQL persistence** with a **stateless LangGraph state machine** located in [`belong-api/onboarding/graph.py`](file:///d:/code/Golang/Belong/belong-api/onboarding/graph.py). 

Rather than maintaining continuous in-memory loops, the system executes **one step per user message**, ensuring stateless isolation between HTTP requests and resilient session recovery.

---

## 1. System Architecture & Component Separation

```text
Client / Frontend
       ↓ (POST /api/onboarding/message)
FastAPI Server (`belong-api/api/routes/onboarding.py`)
       ↓
1. Fetch conversation progress from PostgreSQL (`conversations` table)
2. Reconstruct transient `OnboardingState` dictionary
       ↓
3. LangGraph Workflow Execution (`belong-api/onboarding/graph.py`)
       ├── Node A: Extract evidence signals (`extract_signals_node`)
       └── Node B: Check vagueness & generate warm reply (`generate_response_node`)
       ↓
4. Persist updated progress back to `conversations` (explicit DB columns)
5. Save incoming & outgoing chat messages to `conversation_messages`
       ↓ (If Onboarding Status == "completed")
6. Finalize Profile (`finalize_profile()`) → Writes to `profiles` table
```

### Component Roles
- **`conversations` Table**: Permanent storage for current onboarding progress and extracted signals.
- **`conversation_messages` Table**: Immutable audit log of the user-assistant chat history.
- **LangGraph**: Workflow engine for executing analytical extraction and natural text generation per message step.
- **`profiles` Table**: Finalized matchmaking profile structure generated upon onboarding completion.

---

## 2. Database Schema

### `conversations` Table
Stores explicit state and progress metrics for each user's onboarding session:

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | `UUID` | Primary Key |
| `user_id` | `UUID` | ID of the onboarding user |
| `status` | `TEXT` | Conversation status (`'active'` or `'completed'`) |
| `current_area_index` | `INT` | Index of current core topic in `ONBOARDING_QUESTIONS` (0-5) |
| `follow_up_count` | `INT` | Count of adaptive follow-ups asked for current topic |
| `covered_areas` | `JSONB` | Array of completed question IDs (e.g. `["q1_values", "q2_lifestyle"]`) |
| `extracted_signals` | `JSONB` | Key-value mapping accumulating extracted user traits and quotes |
| `created_at` | `TIMESTAMPTZ` | Session start timestamp |
| `updated_at` | `TIMESTAMPTZ` | Last state update timestamp |

### `conversation_messages` Table
Stores raw message history for session resumption and auditability:

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | `UUID` | Primary Key |
| `conversation_id` | `UUID` | Foreign Key to `conversations.id` |
| `role` | `TEXT` | Message sender (`'user'` or `'assistant'`) |
| `content` | `TEXT` | Raw message content |
| `question_id` | `TEXT` | Associated topic ID (e.g. `'q1_values'`) |
| `created_at` | `TIMESTAMPTZ` | Timestamp of message |

---

## 3. LangGraph Workflow Nodes

When invoked via `onboarding_graph.ainvoke(reconstructed_state)`, the graph executes two sequential nodes:

### Node A: Signal Extraction (`extract_signals_node`)
- **Objective**: Extracts structured compatibility evidence from the latest user message.
- **Target Dimensions**: Evaluates user input against target attributes defined for the active core topic (e.g., `self.conflict_style`, `wants.partner_traits`).
- **Anti-Hallucination**: The extraction prompt strictly requires verbatim `quote` evidence from the user's input. Extracted items are appended to `extracted_signals`.

### Node B: Vagueness Evaluation & Response Generation (`generate_response_node`)
1. **Vagueness Check (Internal LLM Call)**:
   - Evaluates if the user's reply lacks detail or depth.
   - If `needs_follow_up == true` AND `follow_up_count < MAX_FOLLOW_UPS` (default 2), the graph retains `current_area_index` and increments `follow_up_count`.
   - If sufficiently detailed (or limit reached), it appends the topic to `covered_areas` and increments `current_area_index`.
2. **Chatbot Response Generation (Conversational LLM Call)**:
   - Generates a warm, empathetic response acknowledging the user's answer while transitioning smoothly into the next question or probing follow-up.

---

## 4. Profile Finalization

When `current_area_index` completes all core onboarding questions:
1. `status` is set to `'completed'`.
2. `finalize_profile()` is invoked to compile accumulated `extracted_signals` into the standardized structure (`self`, `wants`, `constraints`).
3. The resulting profile is stored in the `profiles` table in PostgreSQL.
4. Background jobs (such as profile vector embedding generation) are queued for downstream matching.
