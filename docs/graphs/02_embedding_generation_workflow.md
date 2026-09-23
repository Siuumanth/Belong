# Deterministic Semantic Serialization & Vector Embedding Pipeline

This document explains the deterministic serialization and asynchronous vector embedding workflow handled by the embedding worker (`belong-workers/workers/embedding_worker.py` and `embeddings/serializer.py`).

---

## 1. Vector Pipeline Workflow Diagram

The embedding generation process translates semi-structured profile JSON into two independent 512-dimensional vector representations (`self_embedding` and `wants_embedding`) using Voyage AI.

```mermaid
flowchart TD
    subgraph Trigger ["1. Trigger & Queue"]
        A["Onboarding Completed<br/>(status = 'completed')"] --> B["FastAPI creates DB Job<br/>(type='embedding', status='pending')"]
        B --> C["Publish message to RabbitMQ<br/>Queue: 'belong.embedding'"]
    end

    subgraph Worker ["2. Embedding Worker Execution"]
        C --> D["JobConsumer receives payload<br/>(user_id, job_id)"]
        D --> E["Fetch raw profile from PostgreSQL<br/>SELECT profile FROM profiles WHERE user_id = ..."]
        
        E --> F["CanonicalSerializer.serialize(profile)"]
        
        F --> G1["serialize_self()<br/>• Values, Lifestyle, Personality<br/>• Interests, Goals, Conflict style<br/>• Provides, Emotional needs"]
        F --> G2["serialize_wants()<br/>• Partner traits, Values, Lifestyle<br/>• Communication, Goals, Dealbreakers"]
        
        G1 --> H1["Deterministic Text Block<br/>'self_text'"]
        G2 --> H2["Deterministic Text Block<br/>'wants_text'"]
    end

    subgraph VoyageAI ["3. Vector Generation"]
        H1 --> I1["Voyage AI API<br/>Model: voyage-3-lite<br/>512 dimensions"]
        H2 --> I2["Voyage AI API<br/>Model: voyage-3-lite<br/>512 dimensions"]
        
        I1 --> J1["self_embedding vector (512 float32)"]
        I2 --> J2["wants_embedding vector (512 float32)"]
    end

    subgraph Persistence ["4. Storage & Next Stage Trigger"]
        J1 & J2 --> K["UPDATE profiles SET<br/>• self_embedding = %s::vector<br/>• wants_embedding = %s::vector<br/>• embedding_source_text = jsonb<br/>• updated_at = NOW()"]
        K --> L["UPDATE jobs SET status = 'completed'"]
        L --> M["Enqueue Matching Job<br/>Queue: 'belong.matching'"]
    end
```

### Explanation of Diagram
1. **Trigger & Message Routing**: When a user's onboarding conversation reaches `completed`, the API stores a pending job row in PostgreSQL and delivers an event to the RabbitMQ `belong.embedding` queue.
2. **Canonical Serialization**: Raw JSON from the `profiles` table is parsed deterministically into two dedicated text sections:
   - `self_text`: Summarizes who the user is and what they bring to a relationship (`self.provides`, `self.values`, etc.).
   - `wants_text`: Summarizes what kind of partner and dynamic the user desires (`wants.partner_traits`, `wants.values`, etc.).
3. **Voyage AI Embedding**: Both text blocks are embedded asynchronously using the `voyage-3-lite` model, producing two 512-dimension vectors.
4. **Database Persistence & Matching Trigger**: Vectors are saved into PostgreSQL via pgvector. Once saved, a downstream matching job is enqueued to `belong.matching`.

---

## 2. Canonical Serialization Detail

The `CanonicalSerializer` enforces strict deterministic ordering and confidence filtering:

```mermaid
flowchart LR
    InJson["Raw Profile JSON<br/>extracted_signals"] --> Filter{"Confidence Check<br/>confidence >= 0.50?"}
    Filter -- "No" --> Drop["Drop Signal<br/>(Prevent noise)"]
    Filter -- "Yes" --> Extract["Extract summary string<br/>Strip quotes & metadata"]
    Extract --> Sort["Deterministic Category Ordering<br/>1. Values<br/>2. Lifestyle<br/>3. Personality<br/>4. Interests<br/>5. Life goals<br/>6. Conflict style<br/>7. Provides<br/>8. Emotional needs"]
    Sort --> OutText["Canonical Plaintext<br/>Standardized delimiters"]
```

### Explanation of Diagram
- Signals with confidence below `0.50` are omitted to avoid vector pollution.
- Categories are formatted in a fixed sequential order so identical underlying traits produce identical text representations across recalculations, preventing vector drift.

---

## 3. Developer Notes

### Dual Vector Strategy (`self` vs `wants`)
Belong deliberately splits profiles into two distinct vector embeddings:
* **`self_embedding`**: Captures the user's personality, behavior, lifestyle, and conflict style.
* **`wants_embedding`**: Captures the user's partner preferences and relationship expectations.

This enables **cross-directional similarity search** during Stage 1 retrieval:
$$\text{Compatibility}(A, B) \approx \text{sim}(A.\text{wants}, B.\text{self}) + \text{sim}(B.\text{wants}, A.\text{self})$$

### Vector Specs
- **Model**: `voyage-3-lite` (Voyage AI).
- **Dimensions**: 512.
- **pgvector Index Type**: HNSW with cosine distance operator (`vector_cosine_ops`).
- **PostgreSQL Column Types**: `vector(512)` on `profiles.self_embedding` and `profiles.wants_embedding`.
