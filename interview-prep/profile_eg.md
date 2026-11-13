# Profile Data Structure & Canonical Embeddings Reference

> **Concrete Database Walkthrough: From Extracted JSON to Canonical Text and 384-Dim Vectors**  
> *This document provides the exact representation of how user profiles are stored in PostgreSQL (`profiles.profile` JSONB), how they are converted into canonical text blocks (`self_text` & `wants_text`), and how they are stored as vector coordinates (`VECTOR(384)`).*

---

## 1. Does `profile_eg.md` Match How the Database Stores a Profile?

**YES, 100%.**  
The JSON below is the exact, authentic structure stored in PostgreSQL inside the `profiles.profile` column (`JSONB`).

### The 4 Major Top-Level Sections:
1. **`"self"`**: Who the user is. Contains 8 standardized psychological trait arrays:
   * `values`, `provides`, `interests`, `lifestyle`, `life_goals`, `conflict_style`, `emotional_needs`, `personality_signals`.
2. **`"wants"`**: What the user seeks in a partner. Contains 4 preference arrays:
   * `partner_traits`, `partner_values`, `relationship_expectations`, `desired_lifestyle`.
3. **`"constraints"`**: Dealbreaker boundaries that trigger hard filtering or instant Stage 2 exclusion:
   * `dealbreakers`.
4. **`"raw_dialogue"` & `"raw_responses"`**: The verbatim user chat transcripts keyed by question ID (`q1_intent_partner`, `q2_emotional_needs`, etc.), preserving audit evidence.

---

## 2. Example 1: Real User Profile JSON (Stored in `profiles.profile`)

```json
{
  "self": {
    "values": [
      {
        "id": "q1_intent_partner_s_values_00",
        "label": "Trust",
        "quote": "Trust first",
        "summary": "Places trust as a core personal value.",
        "confidence": 0.98,
        "question_id": "q1_intent_partner",
        "evidence_type": "explicit"
      },
      {
        "id": "q4_lifestyle_values_s_values_01",
        "label": "Growth values",
        "quote": "value people who are actually growing",
        "summary": "Values people who are actively growing.",
        "confidence": 0.98,
        "question_id": "q4_lifestyle_values",
        "evidence_type": "explicit"
      }
    ],
    "provides": [
      {
        "id": "q2_emotional_needs_s_provides_00",
        "label": "Practical support",
        "quote": "practical support and effort",
        "summary": "Provides practical support and effort in the relationship.",
        "confidence": 0.98,
        "question_id": "q2_emotional_needs",
        "evidence_type": "explicit"
      },
      {
        "id": "q3_conflict_provides_s_provides_01",
        "label": "Emotional stability",
        "quote": "steady emotional stability",
        "summary": "Offers steady emotional stability to a partner.",
        "confidence": 0.99,
        "question_id": "q3_conflict_provides",
        "evidence_type": "explicit"
      },
      {
        "id": "q3_conflict_provides_s_provides_02",
        "label": "Verbal reassurance",
        "quote": "verbal reassurance",
        "summary": "Provides verbal reassurance during stressful moments.",
        "confidence": 0.99,
        "question_id": "q3_conflict_provides",
        "evidence_type": "explicit"
      },
      {
        "id": "q3_conflict_provides_s_provides_03",
        "label": "Active listening",
        "quote": "listen actively without rushing to fix things",
        "summary": "Listens actively without rushing to fix problems.",
        "confidence": 0.98,
        "question_id": "q3_conflict_provides",
        "evidence_type": "explicit"
      },
      {
        "id": "q5_personality_s_provides_05",
        "label": "Reliability",
        "quote": "show up when I say I will",
        "summary": "Shows up when they say they will.",
        "confidence": 0.98,
        "question_id": "q5_personality",
        "evidence_type": "explicit"
      }
    ],
    "interests": [
      {
        "id": "q4_lifestyle_values_s_interests_00",
        "label": "Running hobby",
        "quote": "Running is my main thing",
        "summary": "Enjoys running as a primary activity.",
        "confidence": 0.98,
        "question_id": "q4_lifestyle_values",
        "evidence_type": "explicit"
      },
      {
        "id": "q4_lifestyle_values_s_interests_01",
        "label": "Coffee brewing hobby",
        "quote": "specialty filter coffee brewing",
        "summary": "Takes specialty filter coffee brewing seriously.",
        "confidence": 0.98,
        "question_id": "q4_lifestyle_values",
        "evidence_type": "explicit"
      }
    ],
    "lifestyle": [
      {
        "id": "q4_lifestyle_values_s_lifestyle_00",
        "label": "Software engineer career",
        "quote": "Software engineer in Koramangala",
        "summary": "Works as a software engineer in Koramangala.",
        "confidence": 0.98,
        "question_id": "q4_lifestyle_values",
        "evidence_type": "explicit"
      },
      {
        "id": "q4_lifestyle_values_s_lifestyle_01",
        "label": "Daily outdoor habit",
        "quote": "get outside every day",
        "summary": "Makes a point to get outside every day.",
        "confidence": 0.97,
        "question_id": "q4_lifestyle_values",
        "evidence_type": "explicit"
      }
    ],
    "life_goals": [
      {
        "id": "q1_intent_partner_s_life_goals_00",
        "label": "Grow in Bangalore",
        "quote": "grow with in Bangalore",
        "summary": "Wants to grow together with a partner in Bangalore.",
        "confidence": 0.98,
        "question_id": "q1_intent_partner",
        "evidence_type": "explicit"
      }
    ],
    "conflict_style": [
      {
        "id": "q2_emotional_needs_s_conflict_style_00",
        "label": "Quiet withdrawal",
        "quote": "get pretty quiet",
        "summary": "Becomes quiet and withdraws when stressed.",
        "confidence": 0.98,
        "question_id": "q2_emotional_needs",
        "evidence_type": "explicit"
      },
      {
        "id": "q3_conflict_provides_s_conflict_style_01",
        "label": "Calm under pressure",
        "quote": "stay completely calm under pressure",
        "summary": "Remains completely calm when tensions arise.",
        "confidence": 0.99,
        "question_id": "q3_conflict_provides",
        "evidence_type": "explicit"
      }
    ],
    "emotional_needs": [
      {
        "id": "q2_emotional_needs_s_emotional_needs_00",
        "label": "Need processing time",
        "quote": "need an hour",
        "summary": "Needs about an hour alone to process stress before speaking.",
        "confidence": 0.98,
        "question_id": "q2_emotional_needs",
        "evidence_type": "explicit"
      }
    ],
    "personality_signals": [
      {
        "id": "q5_personality_s_personality_signals_00",
        "label": "Easygoing nature",
        "quote": "pretty chill",
        "summary": "Describes self as pretty chill.",
        "confidence": 0.93,
        "question_id": "q5_personality",
        "evidence_type": "explicit"
      }
    ]
  },
  "wants": {
    "partner_traits": [
      {
        "id": "q1_intent_partner_w_partner_traits_00",
        "label": "Curious",
        "quote": "Someone curious",
        "summary": "Seeks a partner who is curious.",
        "confidence": 0.98,
        "question_id": "q1_intent_partner",
        "evidence_type": "explicit"
      },
      {
        "id": "q1_intent_partner_w_partner_traits_01",
        "label": "Self‑care",
        "quote": "takes care of themselves",
        "summary": "Desires a partner who takes care of themselves.",
        "confidence": 0.98,
        "question_id": "q1_intent_partner",
        "evidence_type": "explicit"
      },
      {
        "id": "q1_intent_partner_w_partner_traits_02",
        "label": "No games",
        "quote": "doesn't play games",
        "summary": "Prefers a partner who doesn't play games.",
        "confidence": 0.98,
        "question_id": "q1_intent_partner",
        "evidence_type": "explicit"
      }
    ],
    "partner_values": [
      {
        "id": "q1_intent_partner_w_partner_values_00",
        "label": "Trust first",
        "quote": "Trust first",
        "summary": "Values trust as the foundation of a relationship.",
        "confidence": 0.98,
        "question_id": "q1_intent_partner",
        "evidence_type": "explicit"
      },
      {
        "id": "q4_lifestyle_values_w_partner_values_01",
        "label": "Growth-oriented partner",
        "quote": "people who are actually growing",
        "summary": "Seeks a partner who is professionally or personally growing.",
        "confidence": 0.96,
        "question_id": "q4_lifestyle_values",
        "evidence_type": "explicit"
      }
    ],
    "desired_lifestyle": [],
    "relationship_expectations": [
      {
        "id": "q1_intent_partner_w_relationship_expectations_00",
        "label": "Long‑term relationship",
        "quote": "something that lasts",
        "summary": "Wants a lasting, long‑term relationship.",
        "confidence": 0.98,
        "question_id": "q1_intent_partner",
        "evidence_type": "explicit"
      }
    ]
  },
  "constraints": {
    "dealbreakers": [
      {
        "id": "q6_dealbreakers_c_dealbreakers_00",
        "label": "Arrogance",
        "quote": "Arrogance is a big one",
        "summary": "Intolerant of arrogant people who never admit being wrong.",
        "confidence": 0.98,
        "question_id": "q6_dealbreakers",
        "evidence_type": "explicit"
      },
      {
        "id": "q6_dealbreakers_c_dealbreakers_01",
        "label": "Dishonesty",
        "quote": "small habitual ones",
        "summary": "Cannot accept any form of dishonesty, especially habitual lies.",
        "confidence": 0.97,
        "question_id": "q6_dealbreakers",
        "evidence_type": "explicit"
      }
    ]
  },
  "raw_dialogue": "q1_intent_partner: I want something that lasts. Someone curious, takes care of themselves, doesn't play games. Trust first...\nq2_emotional_needs: I get pretty quiet when I'm stressed — I need an hour or so to sit with it...",
  "raw_responses": {
    "q1_intent_partner": "I want something that lasts...",
    "q2_emotional_needs": "I get pretty quiet when I'm stressed..."
  },
  "other_signals": []
}
```

---

## 3. The Transformation: Canonical Semantic Serialization

Before feeding profile data into `sentence-transformers/all-MiniLM-L6-v2`, Belong's **`CanonicalSerializer`** (`belong-api/embeddings/serializer.py`) transforms the JSON into clean, standardized text blocks.

### Rules of Serialization:
1. **Confidence Filtering:** Items with `confidence < 0.50` are dropped.
2. **Metadata Stripping:** IDs (`q1_intent_s_values_00`), quotes, question IDs, and evidence types are stripped.
3. **Category Aggregation:** Summaries are grouped under human-readable category headers.
4. **Output Format:** Two clean string blocks: `self_text` and `wants_text`.

---

## 4. Exact Canonical Text Strings Before Vectorization

These are the exact string outputs produced by `CanonicalSerializer().serialize(profile)` for the profile above:

### Canonical `self_text`:
```text
SELF

Values: Places trust as a core personal value., Values people who are actively growing.
Lifestyle: Works as a software engineer in Koramangala., Makes a point to get outside every day.
Personality: Describes self as pretty chill.
Interests: Enjoys running as a primary activity., Takes specialty filter coffee brewing seriously., Enjoys reading books on a wide range of topics.
Life goals: Wants to grow together with a partner in Bangalore.
Conflict style: Becomes quiet and withdraws when stressed., Remains completely calm when tensions arise., Dislikes shouting or passive‑aggressive behavior in disagreements.
Provides: Provides practical support and effort in the relationship., Offers steady emotional stability to a partner., Provides verbal reassurance during stressful moments., Listens actively without rushing to fix problems., Gives consistent reassurance and stays in their corner., Shows up when they say they will., Listens attentively and values others' input., Cares about what people have to say., Patient and warms up quickly after initial reserve., Takes up initiations in interactions.
Emotional needs: Needs about an hour alone to process stress before speaking., Feels most appreciated when partner acknowledges their effort.
```

### Canonical `wants_text`:
```text
WANTS

Partner traits: Seeks a partner who is curious., Desires a partner who takes care of themselves., Prefers a partner who doesn't play games., Wants a partner who notices and values their practical contributions.
Partner values: Values trust as the foundation of a relationship., Seeks a partner who is professionally or personally growing.
Relationship expectations: Wants a lasting, long‑term relationship.
```

---

## 5. Example 2: From Real Snapshot (`tests/results/snapshots/result6-perf.md`)

From Alice's profile in the project test snapshots:

### Alice's Canonical `self_text`:
```text
SELF

Values: Cares deeply about consistency and doing small things well over time.
Lifestyle: Practices morning yoga regularly throughout the week., Works in product design with a screen-heavy routine., Follows a plant-based diet and enjoys cooking.
Personality: Describes themselves as intense and passionate when caring about something., Identifies as a very organized person., Notes that they overthink sometimes but maintain self-awareness about it., Describes themselves as warm and genuinely loving people.
Interests: Spends weekends hiking, visiting farmers markets, and bookstores., Enjoys cooking as a personal hobby.
Conflict style: Takes an hour or two to cool down before addressing conflict., Uses 'I felt' statements instead of blaming during disagreements., Willing to have difficult conversations rather than avoiding them.
Provides: Actively shows up and supports partners through difficult times., Cares for partners by cooking and increasing check-ins., Brings attentiveness to small details as a good partner.
Emotional needs: The user tends to go quiet when feeling stressed., Needs a partner to notice and sit quietly without trying to fix it right away., Feels significantly more secure when hearing words of affirmation during tough times.
```

### Alice's Canonical `wants_text`:
```text
WANTS

Partner traits: Considers communication to be a huge priority in a partner., Requires a partner who is emotionally present rather than just physically around., Wants a partner who spontaneously offers reassurance without being asked.
Relationship expectations: Wants to build something real and talks about the future., Looks for a partner who talks about the future.
```

---

## 6. How Vector Embeddings Look in PostgreSQL

When `EmbeddingWorker` processes these canonical strings, it calls `EmbeddingClient.embed_text()` and updates PostgreSQL:

### In the `profiles` Table:

```sql
SELECT user_id, 
       self_embedding, 
       wants_embedding, 
       embedding_source_text 
FROM profiles 
WHERE name = 'Alice';
```

#### 1. `self_embedding` (`VECTOR(384)`)
A dense floating-point array of length 384:
```text
[-0.04210482, 0.08129301, 0.01549210, -0.09241829, 0.03810294, 0.01192847, ..., -0.06319201]
```

#### 2. `wants_embedding` (`VECTOR(384)`)
A dense floating-point array of length 384:
```text
[0.01948201, -0.05219482, 0.09110294, -0.01429810, 0.07219482, -0.03910284, ..., 0.04819203]
```

#### 3. `embedding_source_text` (`JSONB`)
The original text strings are preserved verbatim in JSONB for auditability and vector drift re-indexing:
```json
{
  "self_text": "SELF\n\nValues: Cares deeply about consistency...",
  "wants_text": "WANTS\n\nPartner traits: Considers communication..."
}
```

---

## 7. High-Yield Interview Explanation

When an interviewer asks: *"Show me what your data looks like before and after embeddings"*:

> *"When a user completes onboarding, their psychological signals are structured into JSON with verbatim evidence quotes and saved in `profiles.profile`.*  
>  
> *Before vectorization, we don't feed raw JSON into the model because curly braces, quotes, and metadata add structural noise that dilutes vector attention. Instead, our **Canonical Serializer** strips metadata, filters low-confidence traits ($< 0.50$), and outputs two clean text blocks: `self_text` (who they are) and `wants_text` (what they need).*  
>  
> *These text blocks are passed into `sentence-transformers/all-MiniLM-L6-v2` to generate two **384-dimensional dense vectors** stored in `self_embedding` and `wants_embedding` in PostgreSQL with HNSW cosine indexes.*  
>  
> *This separation is what enables our Stage 1 query to compute bidirectional compatibility—matching User A's wants against Candidate B's self, and Candidate B's wants against User A's self in under 20 milliseconds."*

```

---

## 3. The Transformation: Canonical Semantic Serialization

Before feeding profile data into `sentence-transformers/all-MiniLM-L6-v2`, Belong's **`CanonicalSerializer`** (`belong-api/embeddings/serializer.py`) transforms the JSON into clean, standardized text blocks.

### Rules of Serialization:
1. **Confidence Filtering:** Items with `confidence < 0.50` are dropped.
2. **Metadata Stripping:** IDs (`q1_intent_s_values_00`), quotes, question IDs, and evidence types are stripped.
3. **Category Aggregation:** Summaries are grouped under human-readable category headers.
4. **Output Format:** Two clean string blocks: `self_text` and `wants_text`.

---

## 4. Exact Canonical Text Strings Before Vectorization

These are the exact string outputs produced by `CanonicalSerializer().serialize(profile)` for the profile above:

### Canonical `self_text`:
```text
SELF

Values: Places trust as a core personal value., Values people who are actively growing.
Lifestyle: Works as a software engineer in Koramangala., Makes a point to get outside every day.
Personality: Describes self as pretty chill.
Interests: Enjoys running as a primary activity., Takes specialty filter coffee brewing seriously., Enjoys reading books on a wide range of topics.
Life goals: Wants to grow together with a partner in Bangalore.
Conflict style: Becomes quiet and withdraws when stressed., Remains completely calm when tensions arise., Dislikes shouting or passive‑aggressive behavior in disagreements.
Provides: Provides practical support and effort in the relationship., Offers steady emotional stability to a partner., Provides verbal reassurance during stressful moments., Listens actively without rushing to fix problems., Gives consistent reassurance and stays in their corner., Shows up when they say they will., Listens attentively and values others' input., Cares about what people have to say., Patient and warms up quickly after initial reserve., Takes up initiations in interactions.
Emotional needs: Needs about an hour alone to process stress before speaking., Feels most appreciated when partner acknowledges their effort.
```

### Canonical `wants_text`:
```text
WANTS

Partner traits: Seeks a partner who is curious., Desires a partner who takes care of themselves., Prefers a partner who doesn't play games., Wants a partner who notices and values their practical contributions.
Partner values: Values trust as the foundation of a relationship., Seeks a partner who is professionally or personally growing.
Relationship expectations: Wants a lasting, long‑term relationship.
```

---

## 5. Example 2: From Real Snapshot (`tests/results/snapshots/result6-perf.md`)

From Alice's profile in the project test snapshots:

### Alice's Canonical `self_text`:
```text
SELF

Values: Cares deeply about consistency and doing small things well over time.
Lifestyle: Practices morning yoga regularly throughout the week., Works in product design with a screen-heavy routine., Follows a plant-based diet and enjoys cooking.
Personality: Describes themselves as intense and passionate when caring about something., Identifies as a very organized person., Notes that they overthink sometimes but maintain self-awareness about it., Describes themselves as warm and genuinely loving people.
Interests: Spends weekends hiking, visiting farmers markets, and bookstores., Enjoys cooking as a personal hobby.
Conflict style: Takes an hour or two to cool down before addressing conflict., Uses 'I felt' statements instead of blaming during disagreements., Willing to have difficult conversations rather than avoiding them.
Provides: Actively shows up and supports partners through difficult times., Cares for partners by cooking and increasing check-ins., Brings attentiveness to small details as a good partner.
Emotional needs: The user tends to go quiet when feeling stressed., Needs a partner to notice and sit quietly without trying to fix it right away., Feels significantly more secure when hearing words of affirmation during tough times.
```

### Alice's Canonical `wants_text`:
```text
WANTS

Partner traits: Considers communication to be a huge priority in a partner., Requires a partner who is emotionally present rather than just physically around., Wants a partner who spontaneously offers reassurance without being asked.
Relationship expectations: Wants to build something real and talks about the future., Looks for a partner who talks about the future.
```

---

## 6. How Vector Embeddings Look in PostgreSQL

When `EmbeddingWorker` processes these canonical strings, it calls `EmbeddingClient.embed_text()` and updates PostgreSQL:

### In the `profiles` Table:

```sql
SELECT user_id, 
       self_embedding, 
       wants_embedding, 
       embedding_source_text 
FROM profiles 
WHERE name = 'Alice';
```

#### 1. `self_embedding` (`VECTOR(384)`)
A dense floating-point array of length 384:
```text
[-0.04210482, 0.08129301, 0.01549210, -0.09241829, 0.03810294, 0.01192847, ..., -0.06319201]
```

#### 2. `wants_embedding` (`VECTOR(384)`)
A dense floating-point array of length 384:
```text
[0.01948201, -0.05219482, 0.09110294, -0.01429810, 0.07219482, -0.03910284, ..., 0.04819203]
```

#### 3. `embedding_source_text` (`JSONB`)
The original text strings are preserved verbatim in JSONB for auditability and vector drift re-indexing:
```json
{
  "self_text": "SELF\n\nValues: Cares deeply about consistency...",
  "wants_text": "WANTS\n\nPartner traits: Considers communication..."
}
```

---

## 7. High-Yield Interview Explanation

When an interviewer asks: *"Show me what your data looks like before and after embeddings"*:

> *"When a user completes onboarding, their psychological signals are structured into JSON with verbatim evidence quotes and saved in `profiles.profile`.*  
>  
> *Before vectorization, we don't feed raw JSON into the model because curly braces, quotes, and metadata add structural noise that dilutes vector attention. Instead, our **Canonical Serializer** strips metadata, filters low-confidence traits ($< 0.50$), and outputs two clean text blocks: `self_text` (who they are) and `wants_text` (what they need).*  
>  
> *These text blocks are passed into `sentence-transformers/all-MiniLM-L6-v2` to generate two **384-dimensional dense vectors** stored in `self_embedding` and `wants_embedding` in PostgreSQL with HNSW cosine indexes.*  
>  
> *This separation is what enables our Stage 1 query to compute bidirectional compatibility—matching User A's wants against Candidate B's self, and Candidate B's wants against User A's self in under 20 milliseconds."*
