# 09. Mock Interview Q&A Bank (Top 25 Questions & Model Answers)

> **The Exact Technical Questions Interviewers Will Ask About Belong**  
> *Memorize these high-impact, punchy answers across System Design, Concurrency, Applied AI, Database Engineering, and Behavioral Deep Dives.*

---

## 📂 Category 1: System Design & Architecture

### Q1: *"Walk me through the architecture of Belong in 90 seconds."*
> **Model Answer:**  
> *"Belong is an AI compatibility matchmaking platform built with a decoupled microservice architecture.  
> 
> All client traffic hits our **Go API Gateway** at port 9000, which handles rate limiting, CORS, and verifies JWT tokens at the edge, injecting a verified `X-User-ID` header downstream.  
> Unauthenticated requests like registration and login route to a lightweight **Go Auth service** using bcrypt and HMAC-SHA256.  
> Protected application routes proxy to **Belong API**, a Python FastAPI service that runs our conversational onboarding state machine using **LangGraph** to extract psychological traits into two distinct representations: who the user is (`SELF`), and what they need in a partner (`WANTS`).  
> 
> Because vector generation and LLM reasoning are computationally expensive, the API enqueues tasks into **RabbitMQ**, which dispatches them to asynchronous **Python Workers**.  
> The worker runs a **Two-Stage Matching Pipeline**: Stage 1 uses PostgreSQL with `pgvector` HNSW cosine indexing to filter 10,000+ candidates down to the top 15 in under 20 milliseconds. Stage 2 takes those 15 candidates and runs deep pairwise reasoning using **Groq LLaMA-3.3-70B** across 4 core relationship dimensions, enforcing verbatim quotes from both users to eliminate hallucinations.  
> Everything is backed by a single **PostgreSQL 16** instance using relational tables, JSONB signals, and pgvector coordinates."*

---

### Q2: *"Why did you use Go for the Gateway and Python for the API and Workers instead of writing everything in a single language?"*
> **Model Answer:**  
> *"It came down to matching the right runtime to the workload characteristics:  
> 1. **Go for the Gateway & Auth:** Go compiles to native machine code and its lightweight goroutines (~2KB memory) handle high-concurrency connection multiplexing and reverse-proxying with minimal latency. Cryptographic operations like JWT signature verification and bcrypt password hashing are CPU-bound and run significantly faster in Go without Python's GIL.  
> 2. **Python for the Backend & Workers:** The entire modern AI and ML ecosystem—LangGraph, Pydantic v2, PyTorch, Hugging Face, and `sentence-transformers`—is Python-first. Writing the AI pipeline in Go would have required writing custom inference runtimes and bindings.  
> The Go Gateway handles the high-volume network perimeter, while Python handles AI reasoning."*

---

### Q3: *"Why use RabbitMQ instead of just using FastAPI's built-in `BackgroundTasks` or Celery?"*
> **Model Answer:**  
> *"FastAPI's in-process `BackgroundTasks` run inside the same Python process as the web server. If 20 users trigger matching simultaneously, PyTorch and LLM network calls would exhaust server threads and CPU, causing HTTP request timeouts for incoming users. Furthermore, if the API container crashes or restarts, all in-memory background tasks are permanently lost.  
> 
> We chose **RabbitMQ** over Celery because we wanted a lightweight, explicit AMQP 0-9-1 broker without Celery's heavy boilerplate and serialization quirks. RabbitMQ gives us:  
> 1. **Fair Dispatch (`prefetch_count=1`):** Workers only take 1 heavy matching job at a time, preventing worker starvation.  
> 2. **Durable Queues & Persistent Delivery:** Messages survive broker restarts.  
> 3. **Clean Decoupling:** API instances can scale independently on cheap nodes, while workers scale on compute-heavy nodes."*

---

### Q4: *"How do you ensure zero message loss if RabbitMQ crashes or drops a connection?"*
> **Model Answer:**  
> *"We implement a **Dual-Persistence Pattern**.  
> When a matching or embedding job is created, Belong API first inserts a row into the PostgreSQL `jobs` table with `status = 'pending'`, and *then* publishes the AMQP message to RabbitMQ.  
> 
> Under normal operation, the worker consumes directly from RabbitMQ in milliseconds. But if RabbitMQ ever crashes, network partitions, or drops a message, we have a **Postgres Fallback Reconciler loop** running in `belong-workers/main.py`. Every 15 seconds, it queries:  
> ```sql
> SELECT id FROM jobs WHERE status = 'pending' AND attempts < 3 ORDER BY created_at ASC FOR UPDATE SKIP LOCKED LIMIT 1;
> ```  
> It claims the job atomically, runs the worker, and updates the status to `'completed'`. Even if RabbitMQ is completely offline, zero tasks are ever lost."*

---

### Q5: *"How would you scale Belong from 1,000 to 1,000,000 active users?"*
> **Model Answer:**  
> *"At 1M users, the bottlenecks would be geographic filtering, vector search, and LLM costs. I would scale the system in three steps:  
> 1. **Database & Spatial Indexing:** Replace the Haversine trigonometric calculation in SQL with **PostGIS** using a `geography(Point, 4326)` column and an `R-Tree / GiST` spatial index (`ST_DWithin`). Add Postgres Read Replicas for `GET /api/matches` queries.  
> 2. **Vector Partitioning:** Shard pgvector tables by metropolitan area or region (e.g., Bangalore, SF, NYC) so vector searches only scan candidates within physical dating range.  
> 3. **Two-Tier Reranking:** Add a lightweight cross-encoder model (like `bge-reranker-base`) between Stage 1 and Stage 2 to narrow 50 recalled candidates down to 5 high-confidence candidates before calling the 70B LLM, cutting Groq API costs by 66%."*

---

## 🤖 Category 2: Applied AI & LLM Engineering

### Q6: *"Why use LangGraph instead of a standard LangChain chain or direct LLM calls?"*
> **Model Answer:**  
> *"Because multi-turn conversational onboarding is a **state machine with loops and conditional branching**, not a linear pipeline.  
> 
> In our onboarding flow, the agent must:  
> 1. Extract signals from the user's message (**Node 1**).  
> 2. Evaluate if the answer was vague (**Node 2**).  
> 3. Conditionally branch: if vague and follow-ups $<2$, loop back and probe deeper; if solid, advance to the next question.  
> 4. Check if high-priority traits (`provides`, `emotional_needs`, `conflict_style`) are missing after core questions, and conditionally trigger adaptive probes.  
> 
> LangGraph gives us first-class state management (`OnboardingState`), cyclical graph compilation, and clean separation between extraction, validation, and response generation."*

---

### Q7: *"How do you prevent the LLM from hallucinating compatibility reasons in Stage 2?"*
> **Model Answer:**  
> *"We enforce strict evidence grounding through schema design and prompt constraints:  
> 1. **Verbatim Quote Requirement:** The output schema requires `evidence_a` and `evidence_b` containing literal quotes from both users' onboarding dialogues. The model cannot say *'Bob is supportive'* without citing Bob's actual quote: *'I cook for them, check in more often'*.  
> 2. **The 'Unclear' Escape Hatch:** The prompt explicitly instructs: *'If User A or B did not mention a trait, classify that dimension as unclear. Do NOT infer or assume.'*  
> 3. **Deterministic Verification:** If cited quotes do not exist in the candidate's profile transcript, the verification node catches and flags the output."*

---

### Q8: *"Why separate `SELF` and `WANTS` into two distinct vector embeddings?"*
> **Model Answer:**  
> *"Because in relationship psychology, **similarity does not equal compatibility**.  
> If you combine a user's entire profile into a single text block and compute cosine similarity, you are measuring how identical two people are. For example, two anxious attachers who both demand constant verbal validation will have high cosine similarity, but their dynamic is notoriously unstable.  
> 
> By generating separate vectors for `SELF` (who I am) and `WANTS` (what I need in a partner), our Stage 1 query calculates **reciprocal fulfillment**:  
> $$\text{Score} = 0.5 \times (\text{User A.wants} \cdot \text{Candidate.self}) + 0.5 \times (\text{Candidate.wants} \cdot \text{User A.self})$$  
> A candidate is only recalled if User A fulfills Candidate B's needs AND Candidate B fulfills User A's needs."*

---

### Q9: *"Why did you choose `all-MiniLM-L6-v2` (384 dimensions) over OpenAI's `text-embedding-3-large` (3072 dimensions)?"*
> **Model Answer:**  
> *"Three reasons: latency, memory footprint, and data privacy:  
> 1. **Memory & Cache Footprint:** 384 dimensions require only $\sim 1.5\text{ KB}$ per vector in Postgres, compared to $\sim 12.2\text{ KB}$ for 3072 dimensions ($8\times$ smaller). This means our HNSW index fits entirely in RAM, enabling $<20\text{ ms}$ queries.  
> 2. **Latency & Cost:** `all-MiniLM-L6-v2` runs locally on CPU in $\sim 15\text{ ms}$ at zero cost, without external network dependencies.  
> 3. **Semantic Density:** For short, canonical psychological summaries (50–150 words), 384 dimensions provide plenty of semantic resolution without the curse of dimensionality."*

---

### Q10: *"How did you handle Groq token limits and 429 rate limit crashes in Stage 2?"*
> **Model Answer:**  
> *"During simulations, evaluating 4 dimensions with rich quotes frequently exceeded Groq's 2048 token ceiling, causing `400 tool_use_failed`. A naive retry immediately hit Groq's burst rate limits (`HTTP 429`), returning an empty string that crashed `json.loads()`.  
> 
> We fixed this with three changes:  
> 1. Raised `max_tokens` to **4096**.  
> 2. Discovered Groq embeds the generated JSON inside the error payload under `failed_generation`. We used regex to extract and repair the JSON directly from the 400 error rather than making a second doomed request.  
> 3. Added `_slim_profile()` to strip non-essential database IDs and confidence floats before prompt assembly, cutting prompt tokens by **50%**."*

---

## 🗄️ Category 3: Database & pgvector Engineering

### Q11: *"Why `pgvector` in PostgreSQL instead of a dedicated vector database like Pinecone or Milvus?"*
> **Model Answer:**  
> *"Because Belong requires **hybrid filtering**: we must filter by mutual age boundaries, mutual gender preferences, and Haversine geographic distance in the exact same query as vector similarity.  
> 
> With a dedicated vector DB like Pinecone, you either have to duplicate all demographic metadata into vector payloads or do a two-database join across the network, leading to consistency drift and synchronization latency.  
> With `pgvector`, hard SQL filters and vector KNN run in a **single unified query plan** inside PostgreSQL with ACID guarantees. Plus, it eliminates the operational burden and SaaS cost of managing a second database."*

---

### Q12: *"What is the difference between HNSW and IVFFlat indexes in pgvector, and why did you choose HNSW?"*
> **Model Answer:**  
> *"IVFFlat clusters vectors into Voronoi cells. It requires a training step on an existing dataset before building the index. If new users join with different profile distributions, recall degrades significantly unless you manually run `REINDEX`.  
> 
> **HNSW** (Hierarchical Navigable Small World) builds a multi-layer graph. It does not require a training step, handles incremental real-time inserts seamlessly as users complete onboarding, and delivers $>95\%$ recall at single-digit millisecond latencies. The trade-off is higher memory usage, but with 384-dimensional vectors, the memory footprint is completely manageable."*

---

### Q13: *"Explain how the `<=>` operator works in pgvector and how your Stage 1 query is structured."*
> **Model Answer:**  
> *"In `pgvector`, the `<=>` operator computes **Cosine Distance**, which equals $1.0 - \text{Cosine Similarity}$.  
> A distance of 0.0 means identical angle, 1.0 means orthogonal, and 2.0 means opposite.  
> 
> In our Stage 1 query in `retrieval.py`, we convert distance to similarity:  
> ```sql
> forward_sim = 1.0 - (p.self_embedding <=> %(wants_vec)s::vector)
> reverse_sim = 1.0 - (p.wants_embedding <=> %(self_vec)s::vector)
> combined_score = (0.5 * forward_sim) + (0.5 * reverse_sim)
> ```  
> The query applies hard SQL filters in the `WHERE` clause (gender normalization, mutual age bounds, and Haversine distance), computes the combined bidirectional score, and orders by `combined_score DESC` to return the top 15 candidates."*

---

### Q14: *"Why store extracted traits in JSONB instead of normalized relational tables (`user_traits`, `traits`)?"*
> **Model Answer:**  
> *"Two reasons: schema elasticity and document atomicity.  
> 1. **Elasticity:** Human psychology doesn't fit static relational columns. Different users reveal completely different traits (e.g., attachment style, sensory habits, career pace). JSONB lets us store emergent insights (`other_signals`) without database migrations.  
> 2. **Point Lookups:** During Stage 1 candidate reduction and Stage 2 reasoning, we need the entire profile document at once. Fetching 15 candidate profiles stored in JSONB requires zero table joins. In a normalized schema with 8 trait tables and evidence quotes, it would require massive multi-table SQL joins."*

---

### Q15: *"What is `SELECT ... FOR UPDATE SKIP LOCKED` and how does your worker reconciler use it?"*
> **Model Answer:**  
> *"It is an atomic row-level locking mechanism in PostgreSQL.  
> When multiple background worker instances poll the `jobs` table for unhandled pending jobs, a standard `SELECT ... FOR UPDATE` would cause workers to block and wait on each other's locks.  
> 
> Adding `SKIP LOCKED` instructs Postgres to skip any row currently locked by another worker transaction and immediately claim the next available row. This allows multiple worker replicas to claim tasks concurrently without race conditions, deadlocks, or distributed Redis locks."*

---

## ⚡ Category 4: Backend, Infrastructure & Concurrency

### Q16: *"How does authentication work end-to-end? How do downstream services know who the user is?"*
> **Model Answer:**  
> *"Belong uses an edge-authenticated perimeter pattern:  
> 1. The client registers or logs in via `POST /auth/login`. The Go Auth service verifies credentials and issues an HMAC-SHA256 signed JWT.  
> 2. On subsequent requests, the client sends `Authorization: Bearer <token>`.  
> 3. The **Go API Gateway** intercepts the request, verifies the token signature, and strips any incoming client `X-User-ID` headers to prevent header spoofing.  
> 4. The Gateway extracts the verified `user_id` claim from the token and injects a sanitized internal header: `X-User-ID: <uuid>`.  
> 5. Downstream FastAPI endpoints read this verified header directly, avoiding redundant JWT decryption and cryptographic overhead."*

---

### Q17: *"Why did you set RabbitMQ `prefetch_count = 1`?"*
> **Model Answer:**  
> *"Because Stage 2 pairwise LLM matching is heavy and takes 15–20 seconds per user run.  
> By default, RabbitMQ dispatches messages round-robin in batches. If 5 users trigger matching at the same time, RabbitMQ would dump all 5 jobs onto Worker 1 while Worker 2 sits completely idle.  
> Setting `prefetch_count=1` enforces fair dispatch: a worker only receives a new job after it sends an explicit `ACK` on its current job. This maximizes parallel throughput across all worker instances."*

---

### Q18: *"How do you handle database migrations across both Go and Python services in Docker Compose?"*
> **Model Answer:**  
> *"We mount our SQL migration scripts into Docker's `/docker-entrypoint-initdb.d/` directory with numeric prefixes:  
> - `00-auth/001_init.sql` (Creates `users` table and `uuid-ossp` extension).  
> - `01-belong/001_...` through `008_...` (Creates `profiles`, `pgvector` extension, HNSW indexes, `jobs`, and `compatibility_results`).  
> 
> In `docker-compose.yml`, both `belong-api` and `belong-workers` define `depends_on` with `condition: service_healthy` on Postgres. Postgres runs `pg_isready` before reporting healthy, guaranteeing all tables and extensions exist before application containers boot."*

---

## 🎯 Category 5: Behavioral & Engineering Leadership

### Q19: *"What was the hardest bug you encountered in Belong, and how did you debug it?"*
> **Model Answer:**  
> *"The hardest bug was the **11-second asynchronous race condition** where simulation matching returned zero results despite successful onboarding.  
> 
> The tricky part was that both the API and worker reported success in isolation. By correlating timestamps across Docker container logs, I realized our Hugging Face embedding worker was hanging on a Docker DNS lookup for 16 seconds before falling back to local vectors, while our test script fired matching after a static 5-second sleep. Stage 1 executed against PostgreSQL before the vectors were written.  
> 
> I fixed it by eliminating static timers in favor of active database readiness polling on `embedding_source_text`, and lowering the external API timeout to 3 seconds with a local deterministic fallback. It taught me never to use sleep timers for synchronization in event-driven systems."*

---

### Q20: *"How did you calibrate LLM confidence scores when the model gave everything a 0.95?"*
> **Model Answer:**  
> *"Our initial prompt asked for a float between 0.8 and 1.0. The LLM naturally anchored to the top of the range, assigning 0.98 to wild inferences like turning 'I walk my dog' into 'Values active outdoors lifestyle'.  
> 
> I solved this by building an explicit **5-band Confidence Calibration Rubric**:  
> - 0.95–1.00: Verbatim word-for-word quote.  
> - 0.80–0.94: Direct paraphrase.  
> - 0.60–0.79: Reasonable inference with context.  
> - $<0.50$: Speculation (dropped by code).  
> 
> I also added an `evidence_type` field (`explicit` vs `inference`). This forced the model to justify its confidence against concrete linguistic anchors."*

---

### Q21: *"What are the biggest limitations of Belong right now?"*
> **Model Answer:**  
> *"Two main limitations:  
> 1. **Sequential Pairwise Evaluation:** In Stage 2, the worker evaluates 15 candidates sequentially, which takes ~15–20 seconds. We can optimize this by evaluating candidates concurrently using `asyncio.gather` bounded by an `asyncio.Semaphore(5)` to cut latency to 4 seconds.  
> 2. **Cold Start Density:** In low-density geographic regions, hard distance and mutual age filters can result in zero recalled candidates. We should implement radius relaxation: if $<5$ candidates are found within 50km, automatically expand the radius to 100km."*

---

### Q22: *"What would you do differently if you rebuilt Belong from scratch?"*
> **Model Answer:**  
> *"I would introduce an intermediate **Cross-Encoder Reranking stage (Stage 1.5)**.  
> Currently, we jump straight from bi-encoder cosine similarity (Stage 1) to a full 70B parameter LLM (Stage 2). Using a lightweight cross-encoder like `bge-reranker-base` would let us score 50 candidates down to 5 in ~50 milliseconds, reducing our expensive 70B LLM calls by 66% while improving candidate precision."*

---

### Q23: *"How did you test your AI matchmaking engine without real human labelers?"*
> **Model Answer:**  
> *"We built an automated **Synthetic Persona Simulation Harness** (`tests/simulators/`).  
> We created golden persona profiles with known relationship dynamics and built `UserSimulator` actors that drive multi-turn onboarding dialogues via HTTP.  
> We then tested **Behavioral Invariants**:  
> 1. *Complementary Pairing (Alice + Bob):* Must produce `strong_alignment`.  
> 2. *Dealbreaker Defense (Eve [non-smoker] + Frank [smoker]):* Frank must be strictly excluded regardless of shared hobbies.  
> 3. *Conflict Clash (Ian [anxious] + Julia [avoidant]):* Must flag a conflict verdict on the communication dimension.  
> If a prompt tweak breaks any of these invariants, our CI test fails immediately."*

---

### Q24: *"What is the difference between similarity and complementarity in relationship matchmaking?"*
> **Model Answer:**  
> *"Similarity means two people have identical traits or desires: both like hiking, or both need emotional reassurance.  
> Complementarity means two people balance each other's needs: Person A needs calm space when stressed, and Person B naturally provides patient, unhurried listening without escalating tension.  
> 
> Most dating apps match on surface similarity. Belong matches on **psychological complementarity**: our matching engine specifically pairs what User A *wants* with what User B naturally *provides*."*

---

### Q25: *"What was your favorite engineering decision in this project?"*
> **Model Answer:**  
> *"Decoupling the Stage 1 vector recall from Stage 2 LLM reasoning.  
> Many developers build AI apps by either doing pure vector search (which misses qualitative relationship nuances) or throwing everything into an LLM prompt (which is slow, expensive, and unscalable).  
> 
> Combining in-database pgvector cosine math for $O(N)$ candidate recall with deep 70B LLM reasoning on only the top 15 candidates gave us the best of both worlds: sub-20ms database recall and deep qualitative reasoning with verified quote citations for under one cent per run."*

