import unittest
import os
import sys

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.normalization_service import (
    normalize_unit_to_mt,
    extract_entity_tuples_from_text,
    UNIT_MULTIPLIERS_TO_MT
)
from app.services.conflict_service import is_generic_mine_name
from app.models.extracted_metric import ExtractedMetric


class TestExtractionAndSemanticGrounding(unittest.TestCase):

    def test_01_unit_multipliers_mathematical_accuracy(self):
        """Verify mathematical integrity of all mining unit multipliers."""
        self.assertEqual(UNIT_MULTIPLIERS_TO_MT["lakh tonnes"], 0.1)
        self.assertEqual(UNIT_MULTIPLIERS_TO_MT["million tonnes"], 1.0)
        self.assertEqual(UNIT_MULTIPLIERS_TO_MT["mt"], 1.0)
        self.assertEqual(UNIT_MULTIPLIERS_TO_MT["thousand tonnes"], 0.001)
        self.assertEqual(UNIT_MULTIPLIERS_TO_MT["tonnes"], 0.000001)
        self.assertEqual(UNIT_MULTIPLIERS_TO_MT["m.cu.m"], 1.0)

    def test_02_unit_normalization_tonnes_precision(self):
        """Verify low-magnitude Tonnes normalization does not round to zero."""
        # 7.99 Tonnes -> 0.000008 MT (not 0.0)
        val, unit = normalize_unit_to_mt(7.99, "Tonnes")
        self.assertEqual(unit, "MT")
        self.assertGreater(val, 0.0)
        self.assertAlmostEqual(val, 0.000008, places=6)

        # 5.41 Tonnes -> 0.000005 MT (not 0.0)
        val2, unit2 = normalize_unit_to_mt(5.41, "Tonnes")
        self.assertEqual(unit2, "MT")
        self.assertGreater(val2, 0.0)
        self.assertAlmostEqual(val2, 0.000005, places=6)

    def test_03_standard_unit_conversions(self):
        """Verify deterministic conversion of Lakh, Million, Thousand Tonnes, and M.Cu.M."""
        # 10 Lakh Tonnes = 1.0 MT
        v1, u1 = normalize_unit_to_mt(10.0, "Lakh Tonnes")
        self.assertEqual(v1, 1.0)
        self.assertEqual(u1, "MT")

        # 42.50 Lakh Tonnes = 4.25 MT
        v2, u2 = normalize_unit_to_mt(42.50, "Lakh Tonnes")
        self.assertEqual(v2, 4.25)
        self.assertEqual(u2, "MT")

        # 167 Million Tonnes = 167.0 MT
        v3, u3 = normalize_unit_to_mt(167.0, "Million Tonnes")
        self.assertEqual(v3, 167.0)
        self.assertEqual(u3, "MT")

        # 500 Thousand Tonnes = 0.5 MT
        v4, u4 = normalize_unit_to_mt(500.0, "Thousand Tonnes")
        self.assertEqual(v4, 0.5)
        self.assertEqual(u4, "MT")

        # 120.40 M.Cu.M = 120.40 M.Cu.M (volume domain preserved)
        v5, u5 = normalize_unit_to_mt(120.40, "M.Cu.M")
        self.assertEqual(v5, 120.40)
        self.assertEqual(u5, "M.Cu.M")

    def test_04_metric_classification_specificity_precedence(self):
        """Verify washery, overburden, dispatch, and drilling take precedence over generic production."""
        # Washing capacity
        sample_washery = "Piparwar washery capacity of 2.0 MT for coal processing was achieved in FY 2023-24."
        tuples = extract_entity_tuples_from_text(sample_washery, page_number=1, default_subsidiary="CCL")
        self.assertGreaterEqual(len(tuples), 1)
        self.assertEqual(tuples[0]["metric_name"], "Washing Capacity")

        # Overburden Removal
        sample_obr = "Rajmahal OC achieved composite overburden removal of 120.40 M.Cu.M during the year."
        tuples_obr = extract_entity_tuples_from_text(sample_obr, page_number=1, default_subsidiary="ECL")
        self.assertGreaterEqual(len(tuples_obr), 1)
        self.assertEqual(tuples_obr[0]["metric_name"], "Overburden Removal")

        # Coal Despatch
        sample_despatch = "Gevra OC recorded total coal despatch of 58.20 MT to power utilities."
        tuples_desp = extract_entity_tuples_from_text(sample_despatch, page_number=1, default_subsidiary="SECL")
        self.assertGreaterEqual(len(tuples_desp), 1)
        self.assertEqual(tuples_desp[0]["metric_name"], "Coal Despatch")

    def test_05_bare_coal_keyword_not_classified_as_production(self):
        """Verify that a sentence containing 'coal' without production context is not forced into Production."""
        sample_text = "The coal ministry allocated capital budget of 1500.00 MT capacity for new railway corridors."
        # Here 'coal' exists as an adjective for the ministry, but there is no production word
        tuples = extract_entity_tuples_from_text(sample_text, page_number=1, default_subsidiary="CIL")
        if tuples:
            self.assertNotEqual(tuples[0]["metric_name"], "Production")

    def test_06_multi_mine_table_separation(self):
        """Verify multi-mine table rows are bound to distinct named entities, not a single page-wide mine."""
        table_text = (
            "Annual Production by Major OpenCast Mines FY 2023-24:\n"
            "Gevra OC recorded coal production of 59.11 MT during the fiscal year.\n"
            "Kusmunda OC recorded coal production of 50.12 MT during the fiscal year.\n"
            "Dipka OC recorded coal production of 33.41 MT during the fiscal year.\n"
        )
        tuples = extract_entity_tuples_from_text(table_text, page_number=1, default_subsidiary="SECL")
        self.assertEqual(len(tuples), 3)

        mine_names = [t["mine_name"] for t in tuples]
        self.assertIn("Gevra OC", mine_names)
        self.assertIn("Kusmunda OC", mine_names)
        self.assertIn("Dipka OC", mine_names)

        # Confirm distinct entities
        self.assertEqual(len(set(mine_names)), 3)

    def test_07_no_synthetic_mine_names_generated(self):
        """Verify absence of specific mine sets 'Unspecified Mine' rather than fabricating 'ECL Mine'."""
        narrative_text = "Eastern Coalfields Limited achieved total coal production of 42.50 Lakh Tonnes in FY 2023-24."
        tuples = extract_entity_tuples_from_text(narrative_text, page_number=1, default_subsidiary="ECL")
        self.assertGreaterEqual(len(tuples), 1)

        extracted_mine = tuples[0]["mine_name"]
        self.assertNotEqual(extracted_mine, "ECL Mine")
        self.assertEqual(extracted_mine, "Unspecified Mine")
        self.assertEqual(tuples[0]["subsidiary"], "ECL")
        self.assertTrue(is_generic_mine_name(extracted_mine))

    def test_08_historical_year_grounding(self):
        """Verify historical inception statement (1975) is NOT stamped as FY 2023-24."""
        hist_snippet = (
            "State-owned coal mining corporate came into being in November 1975 with the Government "
            "taking over private coal mines. With a modest production of 79 MT at the year of its inception "
            "CIL today is the single largest coal producer in the world."
        )
        tuples = extract_entity_tuples_from_text(hist_snippet, page_number=1, default_subsidiary="CIL", default_year="2023-24")
        self.assertGreaterEqual(len(tuples), 1)

        hist_tuple = tuples[0]
        self.assertEqual(hist_tuple["numeric_value"], 79.0)
        self.assertNotEqual(hist_tuple["fiscal_year"], "2023-24")
        self.assertIn("1975", hist_tuple["fiscal_year"])
        self.assertEqual(hist_tuple["validation_status"], "UNVERIFIED")
        self.assertLess(hist_tuple["confidence_score"], 0.80)

    def test_09_dynamic_confidence_and_validation_status(self):
        """Verify grounded records receive VALIDATED (>0.80) while ambiguous receive UNVERIFIED."""
        grounded_text = "Rajmahal OC recorded total Coal Production of 42.50 Lakh Tonnes in FY 2023-24."
        g_tuples = extract_entity_tuples_from_text(grounded_text, page_number=1, default_subsidiary="ECL", default_year="2023-24")
        self.assertGreaterEqual(len(g_tuples), 1)
        self.assertGreaterEqual(g_tuples[0]["confidence_score"], 0.80)
        self.assertEqual(g_tuples[0]["validation_status"], "VALIDATED")

        ambiguous_text = "Overall total reached 5.41 Tonnes in some areas."
        a_tuples = extract_entity_tuples_from_text(ambiguous_text, page_number=1, default_subsidiary="CIL", default_year="2023-24")
        self.assertGreaterEqual(len(a_tuples), 1)
        self.assertEqual(a_tuples[0]["validation_status"], "UNVERIFIED")
        self.assertLess(a_tuples[0]["confidence_score"], 0.80)

    def test_10_database_model_column_precision(self):
        """Verify ExtractedMetric model schema definition has enhanced precision."""
        std_val_col = ExtractedMetric.__table__.columns["standard_value"]
        num_val_col = ExtractedMetric.__table__.columns["numeric_value"]

        self.assertEqual(std_val_col.type.precision, 16)
        self.assertEqual(std_val_col.type.scale, 6)
        self.assertEqual(num_val_col.type.precision, 16)
        self.assertEqual(num_val_col.type.scale, 4)


if __name__ == "__main__":
    unittest.main()
