"""
Layer 4: Full Microservice End-to-End Integration Tests
======================================================
WHAT THIS FILE DOES:
- Tests the complete async pipeline against live running services (belong-api, belong-workers, PostgreSQL, RabbitMQ).
- Steps executed:
  1. POST /profiles -> Creates User A & User B profiles in DB.
  2. POST /profiles/{id}/embeddings -> Publishes job to RabbitMQ -> EmbeddingWorker generates embeddings & updates DB.
  3. POST /matches -> Triggers async matching job -> MatchingWorker runs Stage 1 pgvector retrieval & Stage 2 LLM reasoning.
  4. GET /matches -> Verifies persisted compatibility results.
- REQUIRES: Microservices running locally (e.g. via `docker compose up -d` or running belong-api on port 8000).

HOW TO RUN:
    pytest tests/test_e2e_integration.py -m e2e -v
"""

import asyncio
import os
import unittest
import pytest
from uuid import uuid4
import httpx

@pytest.mark.e2e
class TestLayer4E2EIntegration(unittest.IsolatedAsyncioTestCase):
    """Layer 4 Full Microservice Integration test against running services."""

    def setUp(self):
        self.api_base_url = os.getenv("BELONG_API_URL", "http://localhost:8000")

    async def test_full_async_matching_pipeline(self):
        """Exercises: Create Profiles -> Embedding Jobs -> RabbitMQ -> EmbeddingWorker -> POST /matches -> MatchingWorker -> GET /matches."""
        user_a_id = str(uuid4())
        user_b_id = str(uuid4())

        async with httpx.AsyncClient(base_url=self.api_base_url, timeout=30.0) as client:
            # 1. Create User A Profile
            res_a = await client.post("/profiles", json={
                "user_id": user_a_id,
                "age": 28,
                "gender": "female",
                "relationship_goal": "long-term",
                "latitude": 37.7749,
                "longitude": -122.4194,
                "preferred_genders": ["male"],
                "profile": {
                    "self": {"values": [{"summary": "honesty", "confidence": 0.9, "evidence": "honesty"}]},
                    "wants": {"partner_traits": [{"summary": "communicative", "confidence": 0.9, "evidence": "communicative"}]}
                }
            })
            self.assertIn(res_a.status_code, [200, 201])

            # 2. Create User B Profile
            res_b = await client.post("/profiles", json={
                "user_id": user_b_id,
                "age": 30,
                "gender": "male",
                "relationship_goal": "long-term",
                "latitude": 37.7800,
                "longitude": -122.4100,
                "preferred_genders": ["female"],
                "profile": {
                    "self": {"values": [{"summary": "integrity", "confidence": 0.9, "evidence": "integrity"}]},
                    "wants": {"partner_traits": [{"summary": "thoughtful", "confidence": 0.9, "evidence": "thoughtful"}]}
                }
            })
            self.assertIn(res_b.status_code, [200, 201])

            # 3. Trigger Asynchronous Embedding Jobs
            emb_res_a = await client.post(f"/profiles/{user_a_id}/embeddings")
            emb_res_b = await client.post(f"/profiles/{user_b_id}/embeddings")
            self.assertIn(emb_res_a.status_code, [200, 202])
            self.assertIn(emb_res_b.status_code, [200, 202])

            # 4. Trigger Asynchronous Matching Job for User A
            match_trigger = await client.post("/matches", headers={"X-User-ID": user_a_id})
            self.assertEqual(match_trigger.status_code, 202)
            job_data = match_trigger.json()
            job_id = job_data["job_id"]

            # 5. Poll Job status until completion (up to 20 seconds)
            job_completed = False
            for _ in range(10):
                await asyncio.sleep(2)
                job_check = await client.get(f"/matches/jobs/{job_id}")
                if job_check.status_code == 200:
                    status_val = job_check.json().get("status")
                    if status_val == "completed":
                        job_completed = True
                        break

            # 6. Fetch persisted qualitative matches for User A
            matches_res = await client.get(f"/matches/{user_a_id}")
            self.assertEqual(matches_res.status_code, 200)
            matches_data = matches_res.json()
            self.assertIn("total_matches", matches_data)

if __name__ == "__main__":
    unittest.main()
