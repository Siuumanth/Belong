# Belong — API Endpoints & Usage Summary

All public requests enter through the **Go API Gateway (`:9000`)**, which validates JWT tokens and forwards traffic to the **Go Auth Service (`:9001`)** or the **Python Belong Service (`:8000`)**.

Full schema and contract definitions: [`docs/openapi.yaml`](file:///d:/code/Golang/Belong/docs/openapi.yaml).

---

## Complete API Reference Table

| Method | Endpoint | Auth Required? | Target Service | Purpose / Use in Short |
| :--- | :--- | :---: | :---: | :--- |
| **GET** | `/health` | No | Go Gateway | Checks Gateway liveness and health. |
| **POST** | `/auth/signup` | No | Go Auth (`:9001`) | Registers a new user with username, email, and password. |
| **POST** | `/auth/login` | No | Go Auth (`:9001`) | Authenticates user; returns JWT token + user info. |
| **POST** | `/profiles` | **Yes (JWT)** | Python (`:8000`) | Creates initial structured profile & deterministic filters. |
| **GET** | `/profiles/{user_id}` | **Yes (JWT)** | Python (`:8000`) | Retrieves full profile with JSONB signals & preferences. |
| **PATCH** | `/profiles/{user_id}` | **Yes (JWT)** | Python (`:8000`) | Updates profile fields; triggers re-embedding if traits change. |
| **POST** | `/onboarding/session` | **Yes (JWT)** | Python (`:8000`) | Starts conversational onboarding session; returns first question. |
| **POST** | `/onboarding/message` | **Yes (JWT)** | Python (`:8000`) | Sends answer to LangGraph; returns next adaptive question. |
| **GET** | `/onboarding/{conversation_id}` | **Yes (JWT)** | Python (`:8000`) | Fetches conversation transcript and current dialogue state. |
| **POST** | `/profiles/{user_id}/embeddings` | **Yes (JWT)** | Python (`:8000`) | Manually triggers canonical serialization & vector generation. |
| **GET** | `/profiles/{user_id}/embeddings` | **Yes (JWT)** | Python (`:8000`) | Retrieves embedding source text, model version, and status. |
| **POST** | `/matches` | **Yes (JWT)** | Python (`:8000`) | Enqueues 2-stage matching job; returns `202 Accepted` + `job_id`. |
| **GET** | `/matches/jobs/{job_id}` | **Yes (JWT)** | Python (`:8000`) | Polls status (`pending`/`running`/`completed`) and gets match results. |
| **GET** | `/matches/{user_id}` | **Yes (JWT)** | Python (`:8000`) | Reads latest persisted compatibility cards & rankings. |


---

## Short Usage Guide

### 1. Authentication Flow
- **`POST /auth/signup`**: Create user account.
  ```json
  { "username": "alex", "email": "alex@belong.ai", "password": "SecretPassword123!" }
  ```
- **`POST /auth/login`**: Obtain JWT token for subsequent API calls.
  ```json
  { "email": "alex@belong.ai", "password": "SecretPassword123!" }
  ```
  *(Pass returned token in headers as `Authorization: Bearer <token>`)*

---

### 2. Conversational Onboarding Flow
- **`POST /onboarding/session`**: Starts the onboarding session.
  ```json
  { "user_id": "<uuid>" }
  ```
- **`POST /onboarding/message`**: Submits user response. The LangGraph agent extracts signals with quoted evidence and returns either the next question or completion signal.
  ```json
  { "conversation_id": "<uuid>", "message": "I want a serious relationship where we grow together." }
  ```
- **`GET /onboarding/{conversation_id}`**: Retrieves chat transcript for audit/resume.

---

### 3. Profile Management Flow
- **`GET /profiles/{user_id}`**: Fetches profile data, deterministic filters (age, location), and qualitative JSONB traits (`self`, `wants`, `constraints`).
- **`PATCH /profiles/{user_id}`**: Updates specific fields (e.g. location, preferences).

---

### 4. Asynchronous Matching Flow
- **`POST /matches`**: Requests matches for a user. Returns HTTP `202 Accepted` immediately so clients never timeout.
  ```json
  { "user_id": "<uuid>", "limit": 5 }
  // Response: { "job_id": "<uuid>", "status": "pending" }
  ```
- **`GET /matches/jobs/{job_id}`**: Client polls this endpoint every 2–3s.
  - While running: `{ "status": "running" }`
  - When finished: Returns ranked candidates with multi-dimensional compatibility cards (emotional needs, values, conflict styles, and quoted evidence).
- **`GET /matches/{user_id}`**: Fetches stored historical matches without re-triggering background worker computation.
