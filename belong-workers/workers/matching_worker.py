# TODO Phase 7/8: Matching Worker
#
# Flow:
#   message: {"job_id": "...", "user_id": "...", "type": "matching"}
#     1. Load user profile from PostgreSQL
#     2. Hard constraint SQL filtering (gender, age range, distance, relationship goal)
#     3. pgvector cosine retrieval: user.wants_embedding <=> candidate.self_embedding
#     4. Candidate reduction: top 100 → narrow to top 10-20
#     5. Pairwise LLM compatibility reasoning (bidirectional: A→B and B→A)
#     6. Persist compatibility_results to PostgreSQL
#     7. Rank results
#     8. Update job status → "completed"
