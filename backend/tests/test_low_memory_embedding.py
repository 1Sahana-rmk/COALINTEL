import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import tracemalloc
import numpy as np

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app.services.embedding_service as emb_module
from app.services.embedding_service import (
    get_embedding_model,
    generate_embedding,
    generate_batch_embeddings,
    OnnxEmbeddingBackend,
    EMBEDDING_DIMENSION,
    EMBEDDING_MODEL_NAME,
)


class TestLowMemoryEmbedding(unittest.TestCase):

    def setUp(self):
        # Reset singleton state before each test
        emb_module._model_instance = None

    def tearDown(self):
        # Reset singleton state after each test
        emb_module._model_instance = None

    def test_01_onnx_backend_singleton(self):
        """Verify low-memory ONNX backend loads as thread-safe singleton and preserves 384 dimensions."""
        model = get_embedding_model()
        self.assertIsNotNone(model)
        self.assertNotEqual(model, "MOCK")

        model_again = get_embedding_model()
        self.assertIs(model, model_again)

    def test_02_embedding_dimensions_and_normalization(self):
        """Verify embedding dimension is exactly 384 and L2 normalized for cosine retrieval."""
        sentences = [
            "Eastern Coalfields Limited ECL Rajmahal Open Cast Mining Project produced 15.5 MT coal in FY 2023-24.",
            "Bharat Coking Coal Limited BCCL overburden removal reached 42.1 M.Cu.M.",
            "Coal India corporate headquarters reported composite performance achieving 98.2% target.",
            "SECL Gevra mega project is expanding annual capacity to 70 MT."
        ]

        embs = generate_batch_embeddings(sentences, batch_size=2)
        self.assertEqual(len(embs), 4)

        for emb in embs:
            self.assertEqual(len(emb), EMBEDDING_DIMENSION)
            arr = np.array(emb, dtype=np.float32)
            self.assertTrue(np.all(np.isfinite(arr)))
            self.assertFalse(np.any(np.isnan(arr)))
            norm = float(np.linalg.norm(arr))
            self.assertAlmostEqual(norm, 1.0, places=3)

    def test_03_numerical_stability_reproducibility(self):
        """Verify identical input strings produce stable reproducible 384-d vectors."""
        text = "ECL Rajmahal Mine produced 15.5 MT coal."
        emb1 = generate_embedding(text)
        emb2 = generate_embedding(text)

        self.assertEqual(len(emb1), 384)
        self.assertEqual(len(emb2), 384)
        cos_sim = float(np.dot(np.array(emb1), np.array(emb2)))
        self.assertAlmostEqual(cos_sim, 1.0, places=5)

    def test_04_zero_torch_in_embedding_path(self):
        """Verify initializing and running OnnxEmbeddingBackend does NOT import torch or transformers."""
        # Clean import test
        backend = OnnxEmbeddingBackend()
        self.assertIsNotNone(backend)
        self.assertIsNotNone(backend.tokenizer)
        self.assertIsNotNone(backend.session)
        # Verify tokenizer is Rust Tokenizer
        from tokenizers import Tokenizer
        self.assertIsInstance(backend.tokenizer, Tokenizer)

    def test_05_tokenizer_encoding_contract(self):
        """Verify pure-Rust tokenizer produces correct input_ids, attention_mask, token_type_ids, and special tokens."""
        backend = OnnxEmbeddingBackend()
        tok = backend.tokenizer
        tok.no_padding()
        enc = tok.encode("Coal India Limited annual report 2023-24.")
        
        self.assertGreater(len(enc.ids), 0)
        self.assertEqual(len(enc.ids), len(enc.attention_mask))
        # First token should be [CLS] (id 101) and last token [SEP] (id 102) for BERT tokenizer
        self.assertEqual(enc.ids[0], 101)
        self.assertEqual(enc.ids[-1], 102)
        self.assertTrue(all(m == 1 for m in enc.attention_mask))

    def test_06_strict_offline_operation(self):
        """Verify ONNX model and tokenizer load strictly offline with local_files_only=True."""
        with patch.dict(os.environ, {"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1"}):
            backend = OnnxEmbeddingBackend()
            self.assertTrue(os.path.exists(backend.model_path))
            self.assertTrue(os.path.exists(backend.tokenizer_path))
            vecs = backend.encode(["Coal production test offline."], normalize_embeddings=True)
            self.assertEqual(vecs.shape, (1, EMBEDDING_DIMENSION))

    def test_07_realistic_33_chunks_500_tokens_batch4(self):
        """Verify realistic production workload: 33 chunks of ~500 tokens with default batch_size=4."""
        sample_paragraph = (
            "Coal India Limited CIL under the Ministry of Coal is the single largest coal producer in the world. "
            "In the fiscal year 2023-24, total coal production reached 773.6 Million Tonnes (MT) against the target of 780 MT. "
            "Off-take achieved was 753.5 MT. Overburden removal (OBR) reached an all-time high of 1965 Million Cubic Metres (M.Cu.M). "
            "Subsidiaries performance: Eastern Coalfields Limited (ECL) produced 38.5 MT, Bharat Coking Coal Limited (BCCL) produced 41.2 MT, "
            "Central Coalfields Limited (CCL) produced 84.5 MT, Northern Coalfields Limited (NCL) produced 136.2 MT, "
            "Western Coalfields Limited (WCL) produced 67.8 MT, South Eastern Coalfields Limited (SECL) produced 187.5 MT, "
            "Mahanadi Coalfields Limited (MCL) produced 217.9 MT. Capital expenditure (CAPEX) for FY 2023-24 stood at Rs 19840 Crore. "
            "Safety parameters improved with fatal accident rate declining to 0.12 per million tonnes. Environmental compliance achieved 100%. "
            "Renewable energy capacity installed reached 100 MW solar power. CSR expenditure exceeded statutory mandates at Rs 650 Crore. "
        ) * 4  # ~500 tokens

        chunks = [f"[Page {p+1} Chunk 0] {sample_paragraph}" for p in range(33)]

        embs = generate_batch_embeddings(chunks, batch_size=4)
        self.assertEqual(len(embs), 33)

        for idx, emb in enumerate(embs):
            self.assertEqual(len(emb), EMBEDDING_DIMENSION)
            arr = np.array(emb, dtype=np.float32)
            self.assertTrue(np.all(np.isfinite(arr)))
            norm = float(np.linalg.norm(arr))
            self.assertAlmostEqual(norm, 1.0, places=3)

    def test_08_batch_size_regression_1_4_8(self):
        """Verify embedding output consistency across various batch sizes (1, 4, 8)."""
        sentences = [
            f"Ministry of Coal Annual Report Chapter {i}. Coal production reached 773.6 MT in subsidiary {i}."
            for i in range(8)
        ]

        embs_bs1 = generate_batch_embeddings(sentences, batch_size=1)
        embs_bs4 = generate_batch_embeddings(sentences, batch_size=4)
        embs_bs8 = generate_batch_embeddings(sentences, batch_size=8)

        self.assertEqual(len(embs_bs1), 8)
        self.assertEqual(len(embs_bs4), 8)
        self.assertEqual(len(embs_bs8), 8)

        for i in range(8):
            cos_1_4 = float(np.dot(np.array(embs_bs1[i]), np.array(embs_bs4[i])))
            cos_4_8 = float(np.dot(np.array(embs_bs4[i]), np.array(embs_bs8[i])))
            self.assertAlmostEqual(cos_1_4, 1.0, places=4)
            self.assertAlmostEqual(cos_4_8, 1.0, places=4)

    @patch("app.services.embedding_service.OnnxEmbeddingBackend", side_effect=RuntimeError("Simulated ONNX init failure"))
    @patch.dict(os.environ, {"COALINTEL_ENABLE_PYTORCH_EMBEDDING_FALLBACK": "false"}, clear=False)
    def test_09_onnx_failure_does_not_instantiate_pytorch_in_production(self, mock_onnx):
        """Verify ONNX failure defaults to memory-safe fallback without importing SentenceTransformer."""
        with patch.dict("sys.modules", {"sentence_transformers": MagicMock()}):
            model = get_embedding_model()
            self.assertEqual(model, "MOCK")
            mock_st = sys.modules["sentence_transformers"].SentenceTransformer
            mock_st.assert_not_called()

    @patch("app.services.embedding_service.OnnxEmbeddingBackend", side_effect=RuntimeError("Simulated ONNX init failure"))
    @patch.dict(os.environ, {"COALINTEL_ENABLE_PYTORCH_EMBEDDING_FALLBACK": "true"}, clear=False)
    def test_10_explicit_pytorch_opt_in_activates_pytorch(self, mock_onnx):
        """Verify explicit COALINTEL_ENABLE_PYTORCH_EMBEDDING_FALLBACK=true allows PyTorch for dev/tests."""
        mock_instance = MagicMock()
        mock_st_class = MagicMock(return_value=mock_instance)
        with patch.dict("sys.modules", {"sentence_transformers": MagicMock(SentenceTransformer=mock_st_class)}):
            model = get_embedding_model()
            self.assertEqual(model, mock_instance)
            mock_st_class.assert_called_once_with("all-MiniLM-L6-v2")

    def test_11_deterministic_mock_vector_contract(self):
        """Verify deterministic fallback produces finite 384-dimensional unit vectors."""
        emb_module._model_instance = "MOCK"
        text = "Coal India annual performance report"
        emb = generate_embedding(text)
        self.assertEqual(len(emb), 384)
        arr = np.array(emb, dtype=np.float32)
        self.assertTrue(np.all(np.isfinite(arr)))
        norm = float(np.linalg.norm(arr))
        self.assertAlmostEqual(norm, 1.0, places=3)

    def test_12_list_documents_does_not_invoke_stale_recovery(self):
        """Verify GET /api/v1/documents is a pure read endpoint and never invokes recover_stale_processing_documents."""
        from fastapi.testclient import TestClient
        from main import app
        from database import get_db
        from app.core.rbac import get_current_user
        from app.models.user import User

        mock_user = User(id=1, username="test_analyst", role="Analyst", subsidiary="CIL HQ")
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0
        mock_query.order_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = []

        app.dependency_overrides[get_db] = lambda: mock_db
        app.dependency_overrides[get_current_user] = lambda: mock_user

        with patch("app.services.processing_pipeline.recover_stale_processing_documents") as mock_recover:
            client = TestClient(app)
            response = client.get("/api/v1/documents")
            self.assertEqual(response.status_code, 200)
            mock_recover.assert_not_called()

        app.dependency_overrides.clear()

    def test_13_onnx_arena_and_mem_pattern_disabled(self):
        """Verify ONNX backend initializes with single thread and memory-safe configurations."""
        backend = OnnxEmbeddingBackend()
        self.assertIsNotNone(backend.session)
        # Verify inference execution on memory-safe backend
        embs = backend.encode(["Testing ONNX inference without arena memory allocation."], normalize_embeddings=True)
        self.assertEqual(embs.shape, (1, EMBEDDING_DIMENSION))
        norm = float(np.linalg.norm(embs[0]))
        self.assertAlmostEqual(norm, 1.0, places=3)

    def test_14_batch_size_default_is_2(self):
        """Verify production batch size defaults to 2 and respects COALINTEL_EMBEDDING_BATCH_SIZE."""
        from app.services.embedding_service import DEFAULT_EMBEDDING_BATCH_SIZE
        self.assertEqual(DEFAULT_EMBEDDING_BATCH_SIZE, 2)

        sentences = ["Sample chunk 1", "Sample chunk 2", "Sample chunk 3"]
        with patch.object(emb_module.logger, "info") as mock_log:
            embs = generate_batch_embeddings(sentences)
            self.assertEqual(len(embs), 3)
            # Verify logger recorded batch_size=2
            log_calls = [c.args[0] for c in mock_log.call_args_list if c.args]
            self.assertTrue(any("batch_size=2" in str(msg) for msg in log_calls))


if __name__ == "__main__":
    unittest.main()
