# 02. End-to-End Data Flow (Simple & Visual Guide)

> **The Plain-English Lifecycle of a Match in Belong**  
> *From Alice signing up, to chatting with the LangGraph guide, generating vectors, running two-stage matching, and seeing Bob on her screen.*

---

## 1. The Big Picture (How Everything Connects)

```
 [ 1. Alice Signs Up ] 
          │
          ▼
 [ 2. Conversational Chat ] ────► LangGraph runs on every message:
          │                       Node 1: Extract traits -> Node 2: Decide next question
          ▼
 [ 3. Profile Compilation ] ───► Packs signals into clean JSON: SELF, WANTS, CONSTRAINTS
          │
          ▼
 [ 4. Hand off to Worker ] ────► Job dropped in RabbitMQ so Alice's screen never freezes
          │
          ▼
 [ 5. Canonical Embeddings ] ──► Strips JSON noise -> sentence-transformers -> 384-dim vectors
          │
          ▼
 [ 6. Stage 1: Fast Filter ] ──► SQL filters (age/distance) + pgvector cosine math
          │                       Reduces 10,000 candidates to Top 15 in under 20ms!
          ▼
 [ 7. Stage 2: Deep LLM ] ─────► LLaMA-3.3 compares Alice & Bob across 4 dimensions
          │                       Enforces verbatim quotes; checks dealbreakers
          ▼
 [ 8. Deterministic Rank ] ────► Python math sorts matches (0 dealbreakers first, then score)
          │
          ▼
 [ 9. Alice Sees Matches! ] ───► Frontend displays rich match cards with quote citations
```

---

## 2. The LangGraph Onboarding Graph (Visualized)

In LangGraph:
* **State** = A shared Python dictionary (the notebook passed between steps).
* **Node** = A Python function that does one job (reads state, calls an LLM, updates state).
* **Edge** = An arrow pointing to what runs next.

Every time Alice types a message and hits send, this exact graph executes:

```
                      Alice sends: "I need honesty and quiet time when stressed"
                                                  │
                                                  ▼
                                   ┌──────────────────────────────┐
                                   │         INPUT STATE          │
                                   │ - user_message: "..."        │
                                   │ - current_question: "Q2"     │
                                   │ - signals: { existing... }   │
                                   │ - follow_up_count: 0         │
                                   └──────────────┬───────────────┘
                                                  │
                                                  ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ NODE 1: extract_signals                                                                              │
│                                                                                                      │
│ 1. LLM reads Alice's message.                                                                        │
│ 2. Extracts facts:                                                                                   │
│    - "Values honesty" (Confidence: 0.95)                                                             │
│    - "Needs quiet time when stressed" (Confidence: 0.98)                                             │
│ 3. Drops garbage: If confidence < 0.50, trash it.                                                    │
│ 4. Clips quotes to 80 chars max (keeps evidence clean).                                              │
│ 5. Writes new facts into state["extracted_signals"].                                                 │
└──────────────────────────────────────────────────┬───────────────────────────────────────────────────┘
                                                  │
                                                  │ (Normal Edge)
                                                  ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ NODE 2: generate_response                                                                            │
│                                                                                                      │
│ "What should the bot say back to Alice?"                                                             │
└──────────────────────────────────────────────────┬───────────────────────────────────────────────────┘
                                                  │
                               ┌──────────────────┴──────────────────┐
                               │                                     │
                    Is Alice's answer vague?                 Is her answer solid?
                    (And follow_ups < 2?)                                    │
                               │                                             ▼
                               ▼                                ┌───────────────────────────┐
                  ┌───────────────────────────┐                 │ Advance to Next Question  │
                  │       PROBE DEEPER        │                 │ (current_area_index + 1)  │
                  │ - Ask a gentle follow-up  │                 └─────────────┬─────────────┘
                  │ - follow_up_count + 1     │                               │
                  └────────────┬──────────────┘                               │
                               │                                              ▼
                               │                                 Are all questions done?
                               │                                 (Check high-priority traits)
                               │                                              │
                               │                        ┌─────────────────────┴─────────────────────┐
                               │                        │                                           │
                               │                 Missing trait?                              All Good!
                               │                 (e.g., no conflict style mentioned)        │
                               │                        │                                           ▼
                               │                        ▼                              ┌─────────────────────────┐
                               │            ┌───────────────────────┐                  │    STATUS = COMPLETED   │
                               │            │ Trigger Adaptive Probe│                  │ 1. Bot says warm goodbye│
                               │            │ (Target the missing   │                  │ 2. Calls finalize_profile│
                               │            │  dimension)           │                  │ 3. Enqueues Embeddings  │
                               │            └───────────┬───────────┘                  └────────────┬────────────┘
                               │                        │                                           │
                               ▼                        ▼                                           ▼
                  ┌─────────────────────────────────────────┐                          ┌─────────────────────────┐
                  │             BOT REPLIES                 │                          │           END           │
                  │  "That makes sense. When you're stressed│                          │  (Turn finished)        │
                  │   what does support look like?"         │                          └─────────────────────────┘
                  └─────────────────────────────────────────┘
```

---

## 3. From Profile JSON to Math Vectors

Once onboarding ends, the system prepares Alice's profile for vector search:

```
  [ Extracted Signals in DB ]
               │
               ▼
  ┌────────────────────────────────────────────────────────────────────────────────────────┐
  │ 1. Compile into JSON (finalize_profile)                                                │
  │    Packs everything into 3 buckets:                                                    │
  │    - SELF: Who Alice is (values, provides, lifestyle, conflict style, emotional needs) │
  │    - WANTS: What Alice wants in a partner (traits, values, relationship expectations)  │
  │    - CONSTRAINTS: Her dealbreakers (non-smoker, honesty)                               │
  └──────────────────────────────────────┬─────────────────────────────────────────────────┘
                                         │
                                         ▼
  ┌────────────────────────────────────────────────────────────────────────────────────────┐
  │ 2. Canonical Serializer (Turn JSON into clean text)                                    │
  │    Raw JSON has brackets and IDs that confuse vector models.                           │
  │    The serializer strips the noise and makes two clean text summaries:                 │
  │                                                                                        │
  │    self_text:                                                                          │
  │    "SELF                                                                               │
  │     Values: Values clear communication, Values consistency.                            │
  │     Provides: Practical support in distress, Pays attention to details.                │
  │     Emotional needs: Needs quiet presence, Words of affirmation."                      │
  │                                                                                        │
  │    wants_text:                                                                         │
  │    "WANTS                                                                              │
  │     Partner traits: Good communicator, Emotionally present, Reassuring.                │
  │     Relationship expectations: Long-term relationship, Talks about future."            │
  └──────────────────────────────────────┬─────────────────────────────────────────────────┘
                                         │
                                         ▼
  ┌────────────────────────────────────────────────────────────────────────────────────────┐
  │ 3. sentence-transformers (all-MiniLM-L6-v2)                                            │
  │    Converts those 2 text blocks into two 384-dimensional math vectors:                 │
  │    - self_embedding:  [-0.042, 0.081, 0.015, ... 384 numbers]                          │
  │    - wants_embedding: [0.019, -0.052, 0.091, ... 384 numbers]                          │
  │    Saved directly into PostgreSQL `profiles` table!                                    │
  └────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. The Two-Stage Matching Pipeline (Visualized)

When Alice clicks "Find Matches", the system runs a two-stage pipeline to avoid burning money or time calling an LLM on 10,000 people:

```
                                 Alice wants matches
                                          │
                                          ▼
                      ┌────────────────────────────────────────┐
                      │        STAGE 1: THE FAST FILTER        │
                      │  (Postgres SQL + pgvector HNSW Index)  │
                      └───────────────────┬────────────────────┘
                                          │
                                          ▼
     ┌────────────────────────────────────────────────────────────────────────┐
     │ 1. Hard SQL Filters (Instant elimination):                             │
     │    - Gender check (Mutual: She likes Men AND Candidate likes Women)    │
     │    - Age check (Both fall within each other's min/max age range)       │
     │    - Distance (Haversine formula <= 50km radius)                       │
     │                                                                        │
     │ 2. Bidirectional Vector Math (<=> Cosine Distance):                    │
     │    - Forward: Does Candidate's SELF match Alice's WANTS?               │
     │    - Backward: Does Alice's SELF match Candidate's WANTS?              │
     │    - Score = (0.5 * Forward) + (0.5 * Backward)                        │
     │                                                                        │
     │ Result: 10,000 users filtered down to Top 15 in under 20 milliseconds! │
     └────────────────────────────────────┬───────────────────────────────────┘
                                          │
                                          ▼ (Only 15 candidates passed to Stage 2)
                      ┌────────────────────────────────────────┐
                      │    STAGE 2: DEEP LLM PAIRWISE CHECK    │
                      │      (Groq API: LLaMA-3.3-70B)         │
                      └───────────────────┬────────────────────┘
                                          │
                                          ▼
     ┌────────────────────────────────────────────────────────────────────────┐
     │ For each of the 15 candidates (e.g., Bob):                             │
     │                                                                        │
     │ 1. Give Alice's profile + Bob's profile to the LLM.                    │
     │ 2. The LLM evaluates 4 core relationship dimensions:                   │
     │    • Emotional Needs: Can Bob handle Alice's stress style?             │
     │    • Core Values: Do their life priorities match?                      │
     │    • Lifestyle: Can their daily routines coexist?                     │
     │    • Conflict Style: What happens when they fight?                     │
     │                                                                        │
     │ 3. Anti-Hallucination Rule:                                            │
     │    Every claim must quote Alice's verbatim words and Bob's verbatim    │
     │    words. If no proof exists, mark it "unclear" (NO guessing).         │
     │                                                                        │
     │ 4. Dealbreaker Check:                                                  │
     │    Does Bob violate any of Alice's hard dealbreakers (or vice versa)?  │
     └────────────────────────────────────┬───────────────────────────────────┘
                                          │
                                          ▼
                      ┌────────────────────────────────────────┐
                      │      DETERMINISTIC RANKING IN CODE     │
                      └───────────────────┬────────────────────┘
                                          │
                                          ▼
     ┌────────────────────────────────────────────────────────────────────────┐
     │ I don't trust an LLM to sort numbers. The code sorts with Python math: │
     │                                                                        │
     │ 1. Dealbreaker Penalty: Anyone with 1+ dealbreakers drops to bottom.   │
     │ 2. Verdict Rank: strong_alignment (4) > partial (3) > unclear > clash. │
     │ 3. Balance: (Good alignments) minus (Potential conflicts).             │
     │ 4. Tie-breaker: Stage 1 vector score.                                  │
     └────────────────────────────────────┬───────────────────────────────────┘
                                          │
                                          ▼
                      ┌────────────────────────────────────────┐
                      │           RESULTS DELIVERED            │
                      │  Alice sees Bob with rich reason card  │
                      │  and exact quotes explaining WHY!      │
                      └────────────────────────────────────────┘
```

---

## 5. Step-by-Step Breakdown in Plain English

### Step 1: Alice Signs Up & Logs In
* **What happens:** Alice types her email and password.
* **Under the hood:** Go Auth service hashes her password with bcrypt, saves her in Postgres `users`, and hands her browser a signed JWT pass.
* **If it fails:** Wrong password $\rightarrow$ 401 Unauthorized.

### Step 2: Starting the Chat
* **What happens:** Alice clicks "Start Onboarding".
* **Under the hood:** Belong API creates a conversation record in Postgres and sends back Question 1 (*"What are you looking for in a relationship?"*).

### Step 3: Alice Replies $\rightarrow$ Node 1 Extracts Signals
* **What happens:** Alice types: *"I need someone who is emotionally present and doesn't play games."*
* **Under the hood:** Node 1 sends her text to Groq LLaMA. The LLM extracts facts (`"Emotionally present"`, `"No games"`), attaches her exact quote, checks confidence ($0.98$), and saves it to the state.
* **If it fails:** If Groq has a momentary glitch, an automatic retry runs with backoff. If it still fails, the bot saves an empty extraction for that turn and continues—Alice's chat never crashes.

### Step 4: Node 2 Decides the Next Move
* **What happens:** Node 2 reads what Alice said.
* **Under the hood:**
  * Did Alice give a vague 2-word answer? If yes (and `follow_up_count < 2`), probe deeper.
  * Did she give a good answer? Move to the next question.
  * Are all core questions done? Check if high-priority traits (like conflict style or emotional support) are missing. If missing, ask a targeted question. If all covered, wrap up!

### Step 5: Finalizing Her Profile
* **What happens:** Alice finishes the conversation.
* **Under the hood:** The bot bundles her extracted facts into `SELF` (who she is), `WANTS` (what she seeks), and `CONSTRAINTS` (dealbreakers), and saves it into the `profiles` table as JSONB.

### Step 6: Handing Off to the Background Worker
* **What happens:** Alice's screen says: *"Processing your profile to find your best matches..."*
* **Under the hood:** Generating vectors and running 15 deep LLM comparisons takes 15–20 seconds. To keep Alice's browser from freezing or timing out, the API creates a ticket in the Postgres `jobs` table and publishes a message to RabbitMQ, immediately returning HTTP 202 to the browser.

### Step 7: Making the Vectors (In the Worker)
* **What happens:** The background worker picks up the ticket.
* **Under the hood:** The `CanonicalSerializer` strips brackets and IDs from Alice's profile JSON and turns it into clean `self_text` and `wants_text`. A small machine learning model (`all-MiniLM-L6-v2`) turns those texts into two 384-dimensional math vectors and updates Postgres.

### Step 8: Stage 1 Candidate Recall (Fast Filter)
* **What happens:** Who in the database could be a match for Alice?
* **Under the hood:** The worker runs one fast SQL query in Postgres:
  1. *Hard Filters:* Filters out wrong genders, incompatible age ranges, and anyone farther than 50km away.
  2. *Vector Math:* Uses `pgvector` to compare Alice's `wants` with candidate `self` vectors, and candidate `wants` with Alice's `self` vector.
  3. *Result:* 10,000 people are filtered down to the **Top 15** in 20 milliseconds!

### Step 9: Stage 2 Deep Pairwise Reasoning (The Intelligence)
* **What happens:** Evaluating the Top 15 candidates one by one.
* **Under the hood:** For each candidate (like Bob), the worker sends Alice's and Bob's profiles to Groq LLaMA-3.3-70B:
  * Evaluates 4 dimensions: Emotional Needs, Core Values, Lifestyle, and Conflict Style.
  * Checks for dealbreakers.
  * Enforces verbatim quotes: the LLM must cite Alice's actual words and Bob's actual words. No making things up!
* **Ranking:** Python math sorts the candidates using a 4-part key:
  1. Zero dealbreakers first.
  2. Highest overall verdict (`strong_alignment` > `partial` > `unclear` > `clash`).
  3. Net alignment (Good matches minus potential conflicts).
  4. Tie-breaker: Stage 1 vector score.

### Step 10: Alice Sees Her Matches
* **What happens:** Alice's phone polls `GET /api/matches/{alice_id}`.
* **Under the hood:** The API returns the ranked list with Bob at the top, showing an explanation card with verified quote citations explaining exactly why they fit!
* **Resilience:** If RabbitMQ ever went down during step 6, the worker's **Postgres Reconciler** loop (`SELECT ... FOR UPDATE SKIP LOCKED`) finds the pending job in Postgres and runs it anyway. Zero lost tasks.
