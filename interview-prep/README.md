# Belong — Comprehensive Interview Preparation Guide

> **Your Complete Technical Playbook for Belong**  
> *"Relationships Over Swiping: AI-Assisted Compatibility Matchmaking"*

Welcome to your interview preparation repository for **Belong** — your strongest project. This directory breaks down every layer of the system into clear, digestible, production-grade technical guides equipped with **text block diagrams**, **code references**, **architectural trade-offs**, and **battle-tested interview answers**.

---

## 📚 Study Roadmap & Document Index

| # | Document | Focus & High-Yield Interview Topics |
| :---: | :--- | :--- |
| **01** | [**01. Overall System Architecture**](file:///d:/code/Golang/Belong/interview-prep/01-overall-architecture.md) | The core thesis, polyglot microservice breakdown (Go Gateway, Go Auth, FastAPI, Python Workers, RabbitMQ, PostgreSQL + pgvector), sync vs async boundaries, and the 2-minute whiteboard walkthrough. |
| **02** | [**02. End-to-End Data Flow**](file:///d:/code/Golang/Belong/interview-prep/02-end-to-end-data-flow.md) | Step-by-step tracing of all 10 stages: registration $\rightarrow$ onboarding turn $\rightarrow$ psychometric signal extraction $\rightarrow$ adaptive probing $\rightarrow$ canonical serialization $\rightarrow$ vector embedding $\rightarrow$ Stage 1 SQL recall $\rightarrow$ Stage 2 LLM reasoning $\rightarrow$ ranked delivery. |
| **03** | [**03. AI & LLM Architecture**](file:///d:/code/Golang/Belong/interview-prep/03-ai-and-llm-architecture.md) | LangGraph state machine implementation, nodes, edges, Pydantic schemas, clinical confidence filtering ($\ge 0.50$), adaptive follow-up cap ($\le 2$), dual-space representation (`SELF` vs `WANTS`), MiniLM embeddings (384-dim), and anti-hallucination quote citations. |
| **04** | [**04. Database & Storage Design**](file:///d:/code/Golang/Belong/interview-prep/04-database-and-storage-design.md) | PostgreSQL 16 schema, ER diagram, why JSONB for psychological traits, `pgvector` HNSW cosine indexing (`<=>`), partial indexes (`is_latest = true`), and the atomic `SKIP LOCKED` job reconciler. |
| **05** | [**05. Backend & Infrastructure**](file:///d:/code/Golang/Belong/interview-prep/05-backend-and-infrastructure.md) | Go API Gateway reverse proxying, JWT validation and sanitized header injection (`X-User-ID`), RabbitMQ exchange/queue topology (`prefetch_count=1`), Docker networking with healthchecks, and why expensive AI tasks are decoupled from HTTP request loops. |
| **06** | [**06. Design Decisions, Trade-offs & Interview Q&A**](file:///d:/code/Golang/Belong/interview-prep/06-design-decisions-tradeoffs-and-interview-qa.md) | The *"Why"* behind every choice (Dual-aspect vs single vector, pgvector vs Pinecone, Two-stage matching vs one prompt), 4 real engineering war stories / bugs, system limitations, and tough curveball questions. |
| **07** | [**07. Testing, Synthetic Evaluation & Simulation Harness**](file:///d:/code/Golang/Belong/interview-prep/07-testing-evaluation-and-simulation.md) | How to test AI without human labelers, multi-turn `UserSimulator` actors, 4 behavioral persona invariants (complementary, dealbreakers, conflict clash, geography), Stage 1 Recall@15 benchmarking, and scaling to 100K+ users. |
| **08** | [**08. Real Issues & Major Design Decisions (The Battle-Tested Log)**](file:///d:/code/Golang/Belong/interview-prep/08-real-issues-and-major-design-decisions.md) | Authentic war stories: 11-second async race condition, Groq token truncation & cascading 429 empty responses, the similarity vs complementarity trap, confidence calibration, profile slimming, and second-person voice. |
| **09** | [**09. Mock Interview Q&A Bank (Top 25 Questions & Model Answers)**](file:///d:/code/Golang/Belong/interview-prep/09-mock-interview-qa-bank.md) | 25 rapid-fire interview questions across System Design, Concurrency, Applied AI, Database Engineering, and Behavioral Deep Dives with word-for-word senior engineer model answers. |
| **REF** | [**Profile & Embedding Data Reference (`profile_eg.md`)**](file:///d:/code/Golang/Belong/interview-prep/profile_eg.md) | Concrete database walkthrough: Extracted Profile JSON (`profiles.profile`), Canonical `self_text` and `wants_text`, and 384-dimensional vector coordinate representation. |

---

## 🎯 60-Second Elevator Pitch (Memorize This)

> *"Belong is an AI-assisted compatibility matchmaking platform designed for serious, long-term relationships, built to solve swipe fatigue and superficial photo-based matching on apps like Tinder and Bumble.*
>
> *Instead of rigid forms, users interact with an adaptive conversational AI guide built on LangGraph that extracts evidence-grounded psychological signals into two distinct profiles: who the user is (`SELF`), and what they need in a partner (`WANTS`).*
>
> *To match users, I built a two-stage pipeline: Stage 1 uses deterministic SQL hard filters and pgvector HNSW cosine distance indexing to rapidly reduce 10,000+ candidates down to the top 15 in under 20 milliseconds. Stage 2 uses an asynchronous Python worker powered by RabbitMQ and Groq LLaMA-3.3 to perform deep pairwise compatibility reasoning across 4 core relationship dimensions, enforcing verbatim quotes from both users to eliminate hallucinations.*
>
> *The entire system is fronted by a high-concurrency Go API Gateway handling JWT validation, rate limiting, and reverse proxying to Python FastAPI and background worker microservices."*

---

## 💡 Quick Tips for the Interview

1. **Draw the ASCII diagrams first:** When asked about your project, immediately sketch out the Gateway $\rightarrow$ FastAPI $\rightarrow$ RabbitMQ $\rightarrow$ Workers $\rightarrow$ Postgres flow from [01-overall-architecture.md](file:///d:/code/Golang/Belong/interview-prep/01-overall-architecture.md).
2. **Emphasize two-way reciprocal matching:** Don't just say "we calculate vector similarity". Say: *"We calculate bidirectional compatibility: User A fulfilling User B's wants, AND User B fulfilling User A's wants."*
3. **Bring up real bugs proactively:** When the interviewer asks *"What was the hardest challenge?"*, talk about the PyTorch event-loop starvation bug or the inverted cosine distance bug from [06-design-decisions-tradeoffs-and-interview-qa.md](file:///d:/code/Golang/Belong/interview-prep/06-design-decisions-tradeoffs-and-interview-qa.md). It instantly proves authenticity and deep systems knowledge.

