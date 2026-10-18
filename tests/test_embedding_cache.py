import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


@unittest.skipUnless(importlib.util.find_spec("numpy") and importlib.util.find_spec("dotenv"), "Embedding cache dependencies are not installed")
class EmbeddingCacheTests(unittest.TestCase):
    def test_repeated_text_reuses_vectors_and_preserves_order(self):
        import numpy as np
        from ir_assistant import embedding

        class FakeModel:
            calls = []

            def __getitem__(self, index):
                return SimpleNamespace(auto_model=SimpleNamespace(config=SimpleNamespace(_commit_hash="fixture")))

            def encode(self, texts, **kwargs):
                self.calls.append(texts)
                return np.array([[len(text), 1] for text in texts], dtype=np.float32)

        model = FakeModel()
        with tempfile.TemporaryDirectory() as temporary, patch.object(embedding, "DATA", Path(temporary)), \
                patch.object(embedding, "embedding_model", return_value=model):
            first = embedding.encode_documents(["revenue", "expense", "revenue"])
            second = embedding.encode_documents(["expense", "revenue"])
            self.assertEqual(len(model.calls), 1)
            self.assertEqual(model.calls[0], ["revenue", "expense"])
            np.testing.assert_array_equal(first[0], first[2])
            np.testing.assert_array_equal(second[0], first[1])


if __name__ == "__main__":
    unittest.main()
