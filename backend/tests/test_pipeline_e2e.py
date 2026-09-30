import unittest
import os
import sys

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.normalization_service import (
    normalize_unit_to_mt,
    extract_entity_tuples_from_text
)
from app.services.chunking_service import chunk_text_by_tokens
from app.services.parsing_service import parse_document_file


class TestDay4PipelineEndToEnd(unittest.TestCase):

    def test_pipeline_data_flow(self):
        """Simulates end-to-end data flow: Raw document text -> Chunks -> Entity Tuple Extraction -> Normalization."""
        sample_doc_pages = [
            {
                "page_number": 1,
                "text": (
                    "Eastern Coalfields Limited (ECL) Annual Report FY 2023-24.\n"
                    "Rajmahal OpenCast Mine recorded total Coal Production of 42.50 Lakh Tonnes.\n"
                    "Overburden Removal achieved 120.40 M.Cu.M during the fiscal year."
                )
            },
            {
                "page_number": 2,
                "text": (
                    "Sonalpur OC achieved production of 38.20 Lakh Tonnes of coal in FY 2023-24.\n"
                    "Despatch reached 3.82 Million Tonnes across all railway sidings."
                )
            }
        ]

        all_chunks = []
        all_metrics = []

        for p_info in sample_doc_pages:
            pg_num = p_info["page_number"]
            pg_text = p_info["text"]

            # Step 1: Chunking
            chunks = chunk_text_by_tokens(pg_text, page_number=pg_num, chunk_size_tokens=50, chunk_overlap_tokens=5)
            all_chunks.extend(chunks)

            # Step 2: Metric Extraction & Unit Normalization
            metrics = extract_entity_tuples_from_text(pg_text, page_number=pg_num, default_subsidiary="ECL")
            all_metrics.extend(metrics)

        # Verify Chunking
        self.assertGreaterEqual(len(all_chunks), 2)
        self.assertEqual(all_chunks[0]["page_number"], 1)

        # Verify Extracted & Normalized Metrics
        self.assertGreaterEqual(len(all_metrics), 2)
        
        # Check Rajmahal OC metric normalization
        rajmahal_metric = next(m for m in all_metrics if "Rajmahal" in m["mine_name"] or m["numeric_value"] == 42.50)
        self.assertEqual(rajmahal_metric["numeric_value"], 42.50)
        self.assertEqual(rajmahal_metric["unit"], "Lakh Tonnes")
        self.assertEqual(rajmahal_metric["standard_value"], 4.25)
        self.assertEqual(rajmahal_metric["standard_unit"], "MT")

        # Check Sonalpur OC metric normalization
        sonalpur_metric = next(m for m in all_metrics if m["numeric_value"] == 38.20)
        self.assertEqual(sonalpur_metric["numeric_value"], 38.20)
        self.assertEqual(sonalpur_metric["standard_value"], 3.82)
        self.assertEqual(sonalpur_metric["standard_unit"], "MT")


if __name__ == "__main__":
    unittest.main()
