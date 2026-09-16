# Developer Guide: Stage 1 Candidate Retrieval & Filtering (`belong-api`)

## 1. Overview

**Stage 1 Matchmaking** is responsible for **Candidate Recall & Hard Filtering**. 

Before running expensive pairwise LLM compatibility reasoning (Stage 2), the system queries PostgreSQL using deterministic SQL hard constraints and fast `pgvector` HNSW cosine similarity search to retrieve and pre-rank the most viable candidates.

```text
User A (Seeking Matches)
         ↓
┌─────────────────────────────────────────────────────────────┐
│                 Stage 1: Candidate Recall                   │
│                                                             │
│  1. Hard Constraint SQL Filters                             │
│     - Mutual gender & orientation alignment                 │
│     - Mutual age boundaries ([min, max])                    │
│     - Haversine geographic distance (<= max_distance_km)    │
│     - Required relationship goal matching                   │
│                                                             │
│  2. pgvector Cosine Nearest-Neighbor Search                 │
│     - Query: User A wants_embedding                         │
│     - Target: Candidate pool self_embedding                 │
│     - Index: HNSW vector_cosine_ops (<=>)                   │
│     - Retrieves pool (default: top 50 candidates)           │
│                                                             │
│  3. Pre-Ranking & Shortlisting                              │
│     - Weighted bidirectional similarity scoring             │
│     - Slices shortlist (default: top 15 candidates)         │
└──────────────────────────────┬──────────────────────────────┘
                               ↓
                 Top Candidates for Stage 2
               (Pairwise LLM Compatibility)
```

---

## 2. Component Structure

The Stage 1 matching logic is located in `belong-api/matching/`:

* **[`models.py`](file:///d:/code/Golang/Belong/belong-api/matching/models.py)**: Defines data schemas (`CandidateMatch`, `RetrievalOptions`).
* **[`retrieval.py`](file:///d:/code/Golang/Belong/belong-api/matching/retrieval.py)**: The `CandidateRetriever` engine executing the SQL query and pre-ranking calculations.
* **[`config.py`](file:///d:/code/Golang/Belong/belong-api/config.py)**: Holds system-wide default thresholds and pool limits.

---

## 3. Hard Filtering Rules

All filters are **bidirectional** (mutually applied to both User A and Candidate B):

| Constraint | User A Rule | Candidate B Rule |
| :--- | :--- | :--- |
| **Gender / Orientation** | Candidate's `gender` in User A's `preferred_genders` | User A's `gender` in Candidate's `preferred_genders` (if set) |
| **Age Range** | Candidate `age` in `[preferred_age_min, preferred_age_max]` | User A `age` in Candidate's `[preferred_age_min, preferred_age_max]` |
| **Relationship Goal** | Candidate `relationship_goal` == User A's `required_relationship_goal` | User A `relationship_goal` == Candidate's `required_relationship_goal` |
| **Distance (Haversine)** | $\text{Distance} \le \text{User A's } \text{max\_distance\_km}$ | $\text{Distance} \le \text{Candidate's } \text{max\_distance\_km}$ |

### Haversine Formula (SQL)
```sql
(6371 * acos(
    LEAST(1.0, GREATEST(-1.0, 
        cos(radians(:user_lat)) * cos(radians(p.latitude)) * 
        cos(radians(p.longitude) - radians(:user_lon)) + 
        sin(radians(:user_lat)) * sin(radians(p.latitude))
    ))
))
```

---

## 4. Vector Similarity & Pre-Ranking

### 1. Primary Vector Search (Recall)
PostgreSQL calculates the cosine distance using the HNSW index on `self_embedding`:
$$\text{cosine\_distance} = \text{self\_embedding} \Leftrightarrow \text{wants\_embedding}$$
$$\text{cosine\_similarity} = \max(0.0, 1.0 - \text{cosine\_distance})$$

### 2. Bidirectional Scoring
If the candidate also has a `wants_embedding` and User A has a `self_embedding`, the retriever calculates reverse similarity:
$$\text{reverse\_similarity} = \max(0.0, 1.0 - (\text{candidate.wants\_embedding} \Leftrightarrow \text{user.self\_embedding}))$$

$$\text{combined\_score} = (1 - w) \cdot \text{cosine\_similarity} + w \cdot \text{reverse\_similarity}$$
*(Where $w = \text{MATCHING\_BIDIRECTIONAL\_WEIGHT}$, default `0.5`)*

---

## 5. Configuration & Runtime Overrides

All parameters are configurable via environment variables or runtime overrides:

```python
from matching.models import RetrievalOptions
from matching.retrieval import CandidateRetriever

# Custom runtime options
options = RetrievalOptions(
    candidate_pool_limit=100,      # Initial pgvector recall pool size
    pre_rank_limit=20,              # Top candidates passed to LLM
    max_distance_km=50,             # Max geo distance in km
    min_similarity_threshold=0.3,   # Minimum similarity score floor
    require_mutual_gender=True,     # Toggle mutual gender filter
    require_mutual_age=True         # Toggle mutual age filter
)

retriever = CandidateRetriever(options=options)
candidates = await retriever.retrieve_candidates(user_id=user_uuid)
```

### Environment Defaults (`config.py`):
```env
MATCHING_CANDIDATE_POOL_LIMIT=50
MATCHING_PRE_RANK_LIMIT=15
MATCHING_MAX_DISTANCE_KM_DEFAULT=100
MATCHING_MIN_SIMILARITY_THRESHOLD=0.0
MATCHING_BIDIRECTIONAL_WEIGHT=0.5
```

---

## 6. Output Schema (`CandidateMatch`)

```json
{
  "user_id": "c3b3e21a-4d7a-4ec6-89d1-0f72365e23ef",
  "age": 28,
  "gender": "female",
  "orientation": "straight",
  "relationship_goal": "long-term",
  "distance_km": 12.4,
  "cosine_distance": 0.15,
  "cosine_similarity": 0.85,
  "reverse_cosine_distance": 0.20,
  "reverse_cosine_similarity": 0.80,
  "combined_score": 0.825,
  "profile": {
    "self": { "values": ["honesty", "growth"], "lifestyle": ["active"] },
    "wants": { "partner_traits": ["emotionally supportive"] }
  }
}
```

---

## 7. Unit Testing

Run retrieval unit tests:
```bash
cd belong-api
python -m unittest discover -s tests -p "test_retrieval.py"
```
