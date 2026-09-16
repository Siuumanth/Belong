import unittest
from embeddings.client import EmbeddingClient

class TestEmbeddingClient(unittest.IsolatedAsyncioTestCase):
    async def test_embedding_client_vector_dimension(self):
        client = EmbeddingClient()
        text = "SELF\n\nValues: honesty, independence.\nLifestyle: active lifestyle."
        
        vec = await client.embed_text(text)
        self.assertIsInstance(vec, list)
        self.assertEqual(len(vec), 384)
        self.assertTrue(all(isinstance(x, float) for x in vec))

    async def test_embedding_client_batch(self):
        client = EmbeddingClient()
        texts = [
            "SELF\n\nValues: honesty.",
            "WANTS\n\nPartner traits: emotionally available."
        ]
        
        vectors = await client.embed_batch(texts)
        self.assertEqual(len(vectors), 2)
        self.assertEqual(len(vectors[0]), 384)
        self.assertEqual(len(vectors[1]), 384)

if __name__ == "__main__":
    unittest.main()
