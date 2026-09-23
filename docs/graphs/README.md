# Belong Architecture & Workflows (Mermaid Graphs)

This directory contains comprehensive architectural diagrams, state machine graphs, sequence diagrams, and developer notes for every workflow and graph in Belong.

Each document includes dedicated Mermaid diagrams, inline explanations for every diagram, and critical developer invariant rules.

---

## Index of Graphs and Workflows

| # | Workflow / Graph | Document | Description |
| :--- | :--- | :--- | :--- |
| **01** | **Onboarding State Machine & Session Lifecycle** | [`01_onboarding_graph_and_workflow.md`](file:///d:/code/Golang/Belong/docs/graphs/01_onboarding_graph_and_workflow.md) | Turn-by-turn HTTP lifecycle, LangGraph 2-node state machine, adaptive behavioral probe, and the 2 follow-up hard cap invariant. |
| **02** | **Deterministic Serialization & Vector Embedding** | [`02_embedding_generation_workflow.md`](file:///d:/code/Golang/Belong/docs/graphs/02_embedding_generation_workflow.md) | Canonical serializer (`self` vs `wants`), Voyage AI `voyage-3-lite` integration, 512-dim pgvector persistence, and matching trigger. |
| **03** | **Stage 1 Candidate Retrieval & Filtering** | [`03_stage1_retrieval_workflow.md`](file:///d:/code/Golang/Belong/docs/graphs/03_stage1_retrieval_workflow.md) | Hard constraint SQL filters (gender, age window, Haversine geo distance) and bidirectional cosine distance scoring math. |
| **04** | **Stage 2 Pairwise Reciprocal Reasoning LangGraph** | [`04_stage2_reasoning_graph_workflow.md`](file:///d:/code/Golang/Belong/docs/graphs/04_stage2_reasoning_graph_workflow.md) | Compiled 3-node LangGraph (`format_prompt` -> `llm_reasoning` -> `validation`), reciprocal alignment matrix ($A.\text{wants} \leftrightarrow B.\text{provides}$), and verbatim quote resolution. |
| **05** | **RabbitMQ Messaging, Workers & DB Reconciler** | [`05_workers_and_rabbitmq_pipeline.md`](file:///d:/code/Golang/Belong/docs/graphs/05_workers_and_rabbitmq_pipeline.md) | Direct exchange topology, prefetch limits, DLQ dead-lettering, and the PostgreSQL `FOR UPDATE SKIP LOCKED` 15-second reconciler. |
| **06** | **End-to-End System Workflow** | [`06_end_to_end_system_workflow.md`](file:///d:/code/Golang/Belong/docs/graphs/06_end_to_end_system_workflow.md) | Comprehensive 5-phase flowchart linking User Onboarding -> RabbitMQ -> Vector Embeddings -> Two-Stage Matchmaking -> Match Discovery API. |
