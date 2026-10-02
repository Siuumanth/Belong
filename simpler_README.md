# Belong — Relationships Over Swiping

> **A modern, compatibility-driven matchmaking system designed for serious, long-term relationships.**

---

## 💔 The Problem with Modern Dating Apps

Most popular dating apps are built like visual slot machines:
- **Superficial Sorting:** Matches are made in split seconds based almost entirely on photos, prompt quips, or generic hobbies.
- **Illusion of Choice & Swipe Fatigue:** Infinite swiping creates burnout, ghosting, and disposable interactions rather than genuine human connections.
- **Surface Similarity vs. Real Compatibility:** Liking the same music, movies, or sports team doesn't mean two people share the same core values, emotional communication, or relationship expectations.

As a result, traditional dating apps excel at quick dates and high user retention, but frequently fail people seeking **deep, intentional, and lasting relationships**.

---

## ❤️ Why Belong is Better for Serious Relationships

Belong flips the script. Instead of treating dating as endless swiping, Belong focuses on **relationship psychology, emotional complementarity, and mutual alignment**:

1. **Emotional & Psychological Complementarity:** Real compatibility isn't just about shared interests—it's about how two people balance each other. For example, if someone needs emotional reassurance during stress, Belong pairs them with a partner whose natural communication style is grounded, patient, and supportive.
2. **Evidence-Based Profiles:** Users don't fill out rigid forms; they talk with an AI guide. The system extracts evidence-grounded insights about who they are (`self`) and what they need in a partner (`wants`).
3. **Mutual Intentionality:** Matching is strictly two-way. A match is only made if **User A fits what User B is seeking AND User B fits what User A is seeking**.

---

## 🔄 The Matchmaking Flow

Belong processes candidate matchmaking through a 4-step pipeline:

```
┌───────────────────────────────────────────────────────────┐
│ 1. Chat & Learn (AI Onboarding)                          │
│    Conversational AI extracts 'self' and 'wants' signals  │
└─────────────────────────────┬─────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────┐
│ 2. Surface Layer Screening                                │
│    Instant SQL filtering (Distance, Age, Gender, Hard Limits)│
└─────────────────────────────┬─────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────┐
│ 3. Two-Way Vector Compatibility (Stage 1 Recall)         │
│    Fast pgvector cosine matching (User A Wants ↔ User B Self)│
└─────────────────────────────┬─────────────────────────────┘
                              │
                              ▼
┌───────────────────────────────────────────────────────────┐
│ 4. Deep Pairwise LLM Analysis (Stage 2 Reasoning)         │
│    On-demand 4-Dimension compatibility assessment         │
└─────────────────────────────┴─────────────────────────────┘
```

### 1. Conversational AI Onboarding
Instead of answering rigid forms, users engage in a natural conversation with an AI guide. The AI parses user responses into two distinct profiles:
- **`self`**: Who you are, your lifestyle habits, core values, emotional tendencies, and conflict resolution style.
- **`wants`**: What you specifically look for and need in a partner for a healthy relationship.

### 2. Surface Layer Screening
Baseline SQL filters immediately remove non-matches based on physical location, age range, gender preference, and explicit dealbreakers.

### 3. Fast Two-Way Vector Matching (Stage 1)
Using `pgvector` distance indexing, the system rapidly calculates bi-directional vector compatibility:
- **Forward Alignment**: Does Candidate B match User A's `wants` vector?
- **Backward Alignment**: Does User A match Candidate B's `wants` vector?

### 4. Deep Pairwise LLM Analysis (Stage 2)
Candidates who pass Stage 1 vector matching are evaluated across **4 core relationship dimensions** using pairwise LLM reasoning:
1. **Emotional Needs**: Support mechanisms, stress handling, and reassurance dynamics.
2. **Core Values**: Principles regarding family, ambition, personal growth, and ethics.
3. **Lifestyle & Routine**: Daily rhythms, habits, social battery, and work-life balance.
4. **Conflict & Communication**: How partners navigate disagreements, process emotions, and discuss issues.

---

## 🏗️ Architecture in Brief

Belong's backend is built with a decoupled, asynchronous microservice architecture designed for scale and fast response times:

![Belong Architecture](images/architecure.png)

### Key Architectural Components

* **Go API Gateway (`:9000`):** Single entry point handling route forwarding, CORS, and JWT authentication token verification.
* **Go Auth Service (`:9001`):** Microservice managing user registration, password hashing, and JWT token issuance.
* **Belong API (`belong-api` - FastAPI `:8000`):** Handles profile updates, AI onboarding conversational graphs (LangGraph), and real-time candidate retrieval.
* **RabbitMQ Message Broker:** Asynchronous message broker queueing embedding generation and LLM matching jobs.
* **Python Workers (`belong-workers`):** Background workers that process vector embedding serialization and execute Stage 1 SQL/vector queries + Stage 2 LLM compatibility reasoning.
* **PostgreSQL + `pgvector`:** Relational storage for profiles, 1536-dimensional semantic vector embeddings (`self_embedding` and `wants_embedding`), and persisted compatibility results.

---

## 🎯 Summary

Belong transforms modern online dating — moving away from superficial swiping toward **compatible, intentional, and lasting relationships**.
