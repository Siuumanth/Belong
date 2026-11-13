# 05. Backend & Infrastructure Engineering

> **Go Gateway, FastAPI Request Lifecycle, RabbitMQ, and Distributed Operations**  
> *Reverse proxying, JWT claim injection, message-broker topology, Docker container orchestration, and fault tolerance.*

---

## 1. The Go API Gateway Architecture (`gateway/`)

The Gateway is the unified, high-concurrency edge router for Belong. Built with **Go** and **Chi Router** (`github.com/go-chi/chi/v5`), it acts as a security perimeter and traffic manager.

```
                           Incoming Client HTTP Request
                                        |
                                        v
+-------------------------------------------------------------------------------+
|                             GATEWAY MIDDLEWARE PIPELINE                       |
|                                                                               |
|  1. RequestIDMiddleware  -> Injects or extracts X-Request-ID UUID             |
|  2. SecurityHeaders      -> Injects HSTS, X-Content-Type-Options, X-Frame     |
|  3. CORSMiddleware       -> Handles Access-Control-Allow-* headers & OPTIONS  |
|  4. LoggingMiddleware    -> Structured access logs via Uber Zap (latency/code)|
|  5. RateLimiter          -> In-memory token bucket / sliding window           |
|  6. JWTMiddleware        -> Extracts Bearer token, validates HMAC-SHA256 alg  |
|  7. AuthZMiddleware      -> Enforces authenticated context on protected paths |
|  8. HeaderInjection      -> Injects X-User-ID, X-Auth-Expires into request    |
+---------------------------------------+---------------------------------------+
                                        |
                 +----------------------+----------------------+
                 | (Public Route)                              | (Protected Route)
                 v                                             v
        ReverseProxy: Auth (:9001)                    ReverseProxy: Belong API (:8000)
        Stripped: /auth/*                             Preserved: /profiles, /onboarding, /matches
```

### Key Gateway Responsibilities:

#### 1. JWT Authentication at the Edge
* Clients send `Authorization: Bearer <token>`.
* The Gateway decodes and verifies the signature using `JWT_SECRET` and algorithm `HMAC-SHA256`.
* **Centralized Security:** Downstream services (FastAPI) do not need to re-validate JWTs or parse crypto tokens. The gateway strips untrusted incoming `X-User-ID` headers and injects a sanitized, verified `X-User-ID` header before proxying.

#### 2. Reverse Proxy Implementation (`net/http/httputil.ReverseProxy`)
In `gateway/internal/proxy/reverse.go`:
```go
func NewReverseProxy(target *url.URL) *httputil.ReverseProxy {
    proxy := httputil.NewSingleHostReverseProxy(target)
    originalDirector := proxy.Director
    proxy.Director = func(req *http.Request) {
        originalDirector(req)
        req.Host = target.Host
        // Forward client IP and original protocol
        if clientIP, _, err := net.SplitHostPort(req.RemoteAddr); err == nil {
            req.Header.Set("X-Forwarded-For", clientIP)
        }
    }
    proxy.ErrorHandler = func(w http.ResponseWriter, r *http.Request, err error) {
        zlog.Error("Reverse proxy forwarding failed", zap.Error(err), zap.String("url", r.URL.String()))
        http.Error(w, "Bad Gateway", http.StatusBadGateway)
    }
    return proxy
}
```

#### 3. Route Mapping in `gateway/internal/router/router.go`
* `/health` $\rightarrow$ Unified Health Check (checks both Auth and Belong API readiness).
* `/auth/*` $\rightarrow$ Strips prefix `/auth` and proxies to Go Auth service (`:9001`).
* `/profiles/*`, `/onboarding/*`, `/matches/*` $\rightarrow$ Passes through `authz.Handle`, injects claims, and proxies to Belong API (`:8000`).
* `/api/*` $\rightarrow$ Strips `/api` and forwards cleanly.

---

## 2. FastAPI Request Lifecycle & Dependency Injection

The core API service (`belong-api`) is built on **FastAPI** (Python 3.12) with asynchronous handlers:

```
1. Request arrives from Gateway with headers:
   X-User-ID: 1f2fe223-49e9-44b8-894e-56baebb94d23
   X-Request-ID: c412d09a-8812...

2. FastAPI Middleware / Dependencies:
   - Extracts and parses UUID from X-User-ID.
   - Attaches X-Request-ID to logger context.

3. Pydantic Request Validation:
   - Incoming JSON body parsed against Pydantic BaseModel (e.g. SendMessageRequest).
   - If invalid, immediately returns HTTP 422 Unprocessable Entity with exact field errors.

4. Business Logic & LangGraph Graph:
   - Handler calls async repository or graph:
     new_state = await onboarding_graph.ainvoke(current_state)

5. Database Query via Async Connection Pool:
   - Uses psycopg async pool: async with get_db_connection() as conn: ...

6. Asynchronous Task Dispatch:
   - If onboarding completed:
     await job_repository.create_job(...)
     await publisher.publish_job(...)

7. Pydantic Response Serialization:
   - Response validated and serialized against Pydantic schema (e.g. SendMessageResponse).
   - Returns HTTP 200 OK or HTTP 201 Created.
```

---

## 3. RabbitMQ Message Broker Topology

Belong uses RabbitMQ for asynchronous task queueing to isolate long-running AI computations.

```
+-----------------------------------------------------------------------------------+
|                              RABBITMQ BROKER TOPOLOGY                             |
+-----------------------------------------------------------------------------------+

     Publisher: Belong API
              |
              | AMQP Publish (Exchange: "belong.jobs")
              v
     +---------------------------------------------------------------+
     |              Direct / Topic Exchange: belong.jobs             |
     +-------------------------------+-------------------------------+
                                     |
              +----------------------+----------------------+
              | Routing Key: "embedding"                    | Routing Key: "matching"
              v                                             v
     +-------------------------------+             +-------------------------------+
     | Queue: belong.embedding       |             | Queue: belong.matching        |
     | (Durable, Persistent msgs)    |             | (Durable, Persistent msgs)    |
     +---------------+---------------+             +---------------+---------------+
                     |                                             |
                     | AMQP Consume (Prefetch = 1)                 | AMQP Consume (Prefetch = 1)
                     v                                             v
     +-------------------------------+             +-------------------------------+
     |       EmbeddingWorker         |             |        MatchingWorker         |
     |  - Canonical Serializer       |             |  - Stage 1 pgvector Recall    |
     |  - sentence-transformers      |             |  - Stage 2 Groq LLM Reasoning |
     +-------------------------------+             +-------------------------------+
```

### Critical AMQP Implementation Details:
1. **Durable Queues & Persistent Delivery:**
   Queues are declared with `durable=True`, and messages are published with `delivery_mode=DeliveryMode.PERSISTENT` (2). If RabbitMQ restarts, message queues survive.
2. **Fair Dispatch via `prefetch_count = 1`:**
   By default, RabbitMQ dispatches messages round-robin regardless of consumer load. Because Stage 2 matching takes 15 seconds per task, a naive queue would dump 10 matching jobs on Worker 1 while Worker 2 sits idle.
   Setting `await channel.set_qos(prefetch_count=1)` ensures a worker is only assigned **one active task at a time**, accepting another only after it sends an explicit `ACK`.
3. **Manual Acknowledgments (`ACK` / `NACK`):**
   * On success: `await message.ack()`.
   * On unrecoverable error: `await message.reject(requeue=False)` (routes to dead-letter exchange).
   * On transient failure: `await message.nack(requeue=True)`.

---

## 4. Why Expensive AI Operations Are Separated from the API Flow

A classic software engineering interview question: *"Why not compute embeddings and run matching right inside the FastAPI endpoint handler?"*

```
+------------------------------------------------------------------------------------+
|               SYNCHRONOUS EMBEDDING / MATCHING (ANTI-PATTERN)                      |
|                                                                                    |
| Client HTTP Request                                                                |
| ──> [ FastAPI Handler ] ──> [ PyTorch Embedding ] ──> [ 15 LLM Calls ] ──> Return  |
|     (Thread locked)         (CPU Spikes 100%)         (Waits 20 seconds)           |
|                                                                                    |
| Impact:                                                                            |
| 1. HTTP 504 Gateway Timeout (Nginx/Gateway timeout typically 30s).                |
| 2. Thread pool starvation: 10 concurrent users exhaust all API worker threads.     |
| 3. A single LLM rate limit crashes the user's HTTP request.                        |
+------------------------------------------------------------------------------------+

+------------------------------------------------------------------------------------+
|               BELONG'S ASYNCHRONOUS DECOUPLED ARCHITECTURE                         |
|                                                                                    |
| Client Request                                                                     |
| ──> [ FastAPI Handler ] ──> Write DB Job ──> Publish MQ ──> Return HTTP 202       |
|                                                               (Total: 15 ms)       |
|                                                                                    |
| [ RabbitMQ Queue ] ──> [ Python Background Worker ] ──> [ Writes Results to DB ]   |
|                        (Scales independently)           (Client polls status)      |
+------------------------------------------------------------------------------------+
```

### The 4 Major Benefits:
1. **Predictable Sub-50ms API Latencies:** The API gateway and FastAPI respond immediately with HTTP 202 Accepted and a `job_id`.
2. **Worker Isolation & Memory Safety:** PyTorch models and CUDA contexts consume significant memory (~1GB). Keeping this out of the web server prevents web instances from suffering OOM (Out-of-Memory) crashes.
3. **Elastic Horizontal Scaling:** You can scale web servers (`belong-api`) to 10 instances on cheap 1-vCPU nodes to handle web traffic, while running 2 high-memory worker instances (`belong-workers`) to crunch matching jobs.
4. **Resilience & Rate-Limit Smoothing:** If Groq's API rate limits requests, RabbitMQ holds the jobs safely. Workers back off exponentially without client HTTP connections dropping.

---

## 5. Docker Compose & Multi-Container Networking

In `docker-compose.yml`, Belong orchestrates 6 containers on a shared bridge network:

```
+-----------------------------------------------------------------------------------+
|                         DOCKER BRIDGE NETWORK: belong-network                     |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  [ postgres:5432 ] <------+------- [ auth:9001 ] <-------+-- [ gateway:9000 ]    |
|    (Healthy)              |          (Depends: postgres) |     (Public port)      |
|                           |                              |                        |
|  [ rabbitmq:5672 ] <------+------- [ belong-api:8000 ] <-+                        |
|    (Healthy)              |          (Depends: postgres,                          |
|                           |           rabbitmq)                                   |
|                           |                                                       |
|                           +------- [ belong-workers ]                             |
|                                      (Depends: postgres,                          |
|                                       rabbitmq, belong-api)                       |
+-----------------------------------------------------------------------------------+
```

### Orchestration Highlights:
1. **Healthcheck-Driven Bootstrapping (`depends_on` with `condition: service_healthy`):**
   * Fast containers often start before databases finish initializing.
   * Belong configures Postgres health check: `pg_isready -U belong_user -d belong`.
   * Configures RabbitMQ health check: `rabbitmq-diagnostics -q ping`.
   * `belong-api` and `belong-workers` only start **after** Postgres and RabbitMQ report healthy, preventing startup crashes.
2. **Shared Volume Mounts:**
   * `./belong-api/db/migrations` is mounted to `/docker-entrypoint-initdb.d/01-belong` for automatic initial schema migrations on fresh container boots.
   * `postgres_data` named volume ensures database persistence across container teardowns.

---

## 6. Error Handling, Retries & Logging Architecture

### Multi-Tiered Retry Strategy:
1. **Network Retries (Gateway):** Go Gateway retries idempotent requests to downstream services before returning 502 Bad Gateway.
2. **LLM Provider Retries (Worker):**
   * `_retry_llm_invoke` executes up to 3 retries with exponential backoff on HTTP 429 (rate limits) or empty responses.
3. **Job Failure Tracking (Database):**
   * If a worker crashes during execution, the job's `attempts` counter increments.
   * If `attempts >= 3`, the job status transitions to `'failed'` with error details saved in `jobs.error`.
4. **Structured Logging:**
   * Go Gateway uses **Uber Zap** (`zlog`) for zero-allocation structured JSON logging.
   * Python services use standardized logging formats: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`.
   * Distributed request correlation: Every request carries `X-Request-ID` across Gateway $\rightarrow$ API $\rightarrow$ Database logs.

