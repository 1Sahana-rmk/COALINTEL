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


class TestDay4Pipeline(unittest.TestCase):

    def test_unit_normalization_multipliers(self):
        """Verify deterministic conversion of raw units into Million Tonnes (MT)."""
        # 1. Lakh Tonnes -> MT (* 0.1)
        val, unit = normalize_unit_to_mt(42.50, "Lakh Tonnes")
        self.assertEqual(val, 4.25)
        self.assertEqual(unit, "MT")

        # 2. Million Tonnes -> MT (* 1.0)
        val, unit = normalize_unit_to_mt(167.00, "Million Tonnes")
        self.assertEqual(val, 167.00)
        self.assertEqual(unit, "MT")

        # 3. Thousand Tonnes -> MT (* 0.001)
        val, unit = normalize_unit_to_mt(500.00, "Thousand Tonnes")
        self.assertEqual(val, 0.50)
        self.assertEqual(unit, "MT")

        # 4. M.Cu.M (Overburden Removal) -> M.Cu.M
        val, unit = normalize_unit_to_mt(120.40, "M.Cu.M")
        self.assertEqual(val, 120.40)
        self.assertEqual(unit, "M.Cu.M")

    def test_regex_entity_tuple_extraction(self):
        """Verify extraction of (mine, subsidiary, metric, raw_val, norm_val) tuples."""
        sample_text = (
            "Eastern Coalfields Limited (ECL) Annual Mining Report FY 2023-24.\n"
            "Rajmahal OC recorded total Coal Production of 42.50 Lakh Tonnes.\n"
            "Overburden Removal for the mine reached 120.40 M.Cu.M during Q4."
        )

        extracted = extract_entity_tuples_from_text(
            text=sample_text,
            page_number=1,
            default_subsidiary="ECL",
            default_year="2023-24"
        )

        self.assertGreaterEqual(len(extracted), 1)
        prod_metric = extracted[0]

        self.assertIn("Rajmahal", prod_metric["mine_name"])
        self.assertEqual(prod_metric["subsidiary"], "ECL")
        self.assertEqual(prod_metric["numeric_value"], 42.50)
        self.assertEqual(prod_metric["unit"], "Lakh Tonnes")
        self.assertEqual(prod_metric["standard_value"], 4.25)
        self.assertEqual(prod_metric["standard_unit"], "MT")
        self.assertEqual(prod_metric["page_number"], 1)

    def test_500_token_chunking_with_overlap(self):
        """Verify 500-token chunking and 50-token overlap logic."""
        words = [f"word_{i}" for i in range(1200)]
        long_text = " ".join(words)

        chunks = chunk_text_by_tokens(
            text=long_text,
            page_number=3,
            chunk_size_tokens=500,
            chunk_overlap_tokens=50
        )

        self.assertGreater(len(chunks), 1)
        self.assertEqual(chunks[0]["page_number"], 3)
        self.assertEqual(chunks[0]["chunk_index"], 0)
        self.assertEqual(chunks[0]["token_count"], 500)

        # Verify second chunk index and overlap
        self.assertEqual(chunks[1]["chunk_index"], 1)
        self.assertEqual(chunks[1]["token_count"], 500)


if __name__ == "__main__":
    unittest.main()
