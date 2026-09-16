import unittest
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock

from matching.models import CandidateMatch, RetrievalOptions
from matching.retrieval import CandidateRetriever
from config import settings

class TestMatchingRetrieval(unittest.IsolatedAsyncioTestCase):
    def test_effective_options_defaults(self):
        retriever = CandidateRetriever()
        opts = retriever._get_effective_options()
        
        self.assertEqual(opts["candidate_pool_limit"], settings.MATCHING_CANDIDATE_POOL_LIMIT)
        self.assertEqual(opts["pre_rank_limit"], settings.MATCHING_PRE_RANK_LIMIT)
        self.assertEqual(opts["max_distance_km"], settings.MATCHING_MAX_DISTANCE_KM_DEFAULT)
        self.assertTrue(opts["require_mutual_gender"])

    def test_effective_options_custom_override(self):
        custom = RetrievalOptions(
            candidate_pool_limit=100,
            pre_rank_limit=20,
            max_distance_km=50,
            require_mutual_gender=False
        )
        retriever = CandidateRetriever(options=custom)
        opts = retriever._get_effective_options()
        
        self.assertEqual(opts["candidate_pool_limit"], 100)
        self.assertEqual(opts["pre_rank_limit"], 20)
        self.assertEqual(opts["max_distance_km"], 50)
        self.assertFalse(opts["require_mutual_gender"])

    def test_candidate_match_model(self):
        cid = uuid4()
        c = CandidateMatch(
            user_id=cid,
            age=28,
            gender="female",
            cosine_distance=0.15,
            cosine_similarity=0.85,
            reverse_cosine_distance=0.20,
            reverse_cosine_similarity=0.80,
            combined_score=0.825
        )
        self.assertEqual(c.user_id, cid)
        self.assertEqual(c.cosine_similarity, 0.85)
        self.assertEqual(c.combined_score, 0.825)

    @patch("matching.retrieval.get_db_connection")
    async def test_retrieve_candidates_user_missing(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cur = AsyncMock()
        mock_cur.fetchone.return_value = None

        mock_cur_ctx = AsyncMock()
        mock_cur_ctx.__aenter__.return_value = mock_cur
        mock_conn.cursor = MagicMock(return_value=mock_cur_ctx)

        mock_conn_ctx = AsyncMock()
        mock_conn_ctx.__aenter__.return_value = mock_conn
        mock_get_conn.return_value = mock_conn_ctx

        retriever = CandidateRetriever()
        user_id = uuid4()

        with self.assertRaises(ValueError):
            await retriever.retrieve_candidates(user_id)

    @patch("matching.retrieval.get_db_connection")
    async def test_retrieve_candidates_pre_ranking_sort(self, mock_get_conn):
        mock_conn = MagicMock()
        mock_cur = AsyncMock()

        user_id = uuid4()
        cand1_id = uuid4()
        cand2_id = uuid4()
        cand3_id = uuid4()

        # User row mock
        mock_cur.fetchone.return_value = {
            "user_id": str(user_id),
            "age": 29,
            "gender": "male",
            "preferred_genders": ["female"],
            "wants_embedding": [0.1] * 384,
            "self_embedding": [0.2] * 384,
            "latitude": 37.7749,
            "longitude": -122.4194,
            "max_distance_km": 50,
            "relationship_goal": "long-term",
            "preferred_age_min": 25,
            "preferred_age_max": 35,
            "required_relationship_goal": "long-term"
        }

        # Candidates pool mock (3 candidates with different distances)
        mock_cur.fetchall.return_value = [
            {
                "user_id": str(cand1_id),
                "age": 27,
                "gender": "female",
                "orientation": "straight",
                "relationship_goal": "long-term",
                "latitude": 37.7800,
                "longitude": -122.4100,
                "profile": {"self": {"values": ["growth"]}},
                "distance_km": 1.2,
                "cosine_distance": 0.40,  # cos_sim = 0.60
                "reverse_cosine_distance": 0.40  # rev_sim = 0.60 -> combined = 0.60
            },
            {
                "user_id": str(cand2_id),
                "age": 30,
                "gender": "female",
                "orientation": "straight",
                "relationship_goal": "long-term",
                "latitude": 37.7700,
                "longitude": -122.4200,
                "profile": {"self": {"values": ["honesty"]}},
                "distance_km": 2.5,
                "cosine_distance": 0.10,  # cos_sim = 0.90
                "reverse_cosine_distance": 0.20  # rev_sim = 0.80 -> combined = 0.85
            },
            {
                "user_id": str(cand3_id),
                "age": 28,
                "gender": "female",
                "orientation": "straight",
                "relationship_goal": "long-term",
                "latitude": 37.7750,
                "longitude": -122.4150,
                "profile": {"self": {"values": ["creativity"]}},
                "distance_km": 0.8,
                "cosine_distance": 0.25,  # cos_sim = 0.75
                "reverse_cosine_distance": 0.35  # rev_sim = 0.65 -> combined = 0.70
            }
        ]

        mock_cur_ctx = AsyncMock()
        mock_cur_ctx.__aenter__.return_value = mock_cur
        mock_conn.cursor = MagicMock(return_value=mock_cur_ctx)

        mock_conn_ctx = AsyncMock()
        mock_conn_ctx.__aenter__.return_value = mock_conn
        mock_get_conn.return_value = mock_conn_ctx

        # Test with pre_rank_limit = 2
        retriever = CandidateRetriever()
        custom_opts = RetrievalOptions(pre_rank_limit=2)
        results = await retriever.retrieve_candidates(user_id, options=custom_opts)

        self.assertEqual(len(results), 2)
        # Verify sorted by combined_score descending: cand2 (0.85) then cand3 (0.70)
        self.assertEqual(results[0].user_id, cand2_id)
        self.assertEqual(results[0].combined_score, 0.85)
        self.assertEqual(results[1].user_id, cand3_id)
        self.assertEqual(results[1].combined_score, 0.70)

if __name__ == "__main__":
    unittest.main()
