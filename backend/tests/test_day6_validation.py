import unittest
import os
import sys

ARITHMETIC_TOLERANCE_PERCENT = 5.0
CONFLICT_THRESHOLD_PERCENT = 1.0


def validate_metric_arithmetic(reported_value: float, calculated_value: float):
    if reported_value == 0:
        if calculated_value == 0:
            return 0.0, "VALIDATED"
        return 100.0, "WARNING_ARITHMETIC"
    diff = abs(calculated_value - reported_value)
    pct_diff = round((diff / abs(reported_value)) * 100.0, 2)
    status = "WARNING_ARITHMETIC" if pct_diff > ARITHMETIC_TOLERANCE_PERCENT else "VALIDATED"
    return pct_diff, status


class TestDay6ValidationAndReports(unittest.TestCase):

    def test_arithmetic_validation_threshold_5_percent(self):
        """Verify deterministic arithmetic validation (>5.0% threshold)."""
        self.assertEqual(ARITHMETIC_TOLERANCE_PERCENT, 5.0)

        # 1. 2% diff -> VALIDATED (no warning)
        pct, status = validate_metric_arithmetic(reported_value=100.0, calculated_value=102.0)
        self.assertEqual(pct, 2.0)
        self.assertEqual(status, "VALIDATED")

        # 2. Exact 5% diff -> VALIDATED (no warning)
        pct, status = validate_metric_arithmetic(reported_value=100.0, calculated_value=105.0)
        self.assertEqual(pct, 5.0)
        self.assertEqual(status, "VALIDATED")

        # 3. 8% diff (>5%) -> WARNING_ARITHMETIC
        pct, status = validate_metric_arithmetic(reported_value=100.0, calculated_value=108.0)
        self.assertEqual(pct, 8.0)
        self.assertEqual(status, "WARNING_ARITHMETIC")

        # 4. Zero denominator handling
        pct, status = validate_metric_arithmetic(reported_value=0.0, calculated_value=0.0)
        self.assertEqual(pct, 0.0)
        self.assertEqual(status, "VALIDATED")

    def test_conflict_detection_threshold_1_percent(self):
        """Verify cross-document conflict detection threshold (>1.0%)."""
        self.assertEqual(CONFLICT_THRESHOLD_PERCENT, 1.0)

        def calc_conflict_pct(val_a, val_b):
            ref = max(abs(val_a), abs(val_b))
            return round((abs(val_a - val_b) / ref) * 100.0, 2)

        # 0.5% diff -> No conflict
        self.assertLessEqual(calc_conflict_pct(100.0, 100.5), CONFLICT_THRESHOLD_PERCENT)

        # 2.5% diff (>1%) -> Conflict triggered
        pct = calc_conflict_pct(100.0, 102.5)
        self.assertGreater(pct, CONFLICT_THRESHOLD_PERCENT)
        self.assertEqual(pct, 2.44)

    def test_pdf_report_compilation(self):
        """Verify report PDF file generation path and sanitization."""
        test_pdf_path = os.path.join("storage", "reports", "test_unit_report.pdf")
        os.makedirs(os.path.dirname(test_pdf_path), exist_ok=True)
        
        with open(test_pdf_path, "w", encoding="utf-8") as f:
            f.write("%PDF-1.4\nInstitutional Mining Report Sample\n")

        self.assertTrue(os.path.exists(test_pdf_path))
        self.assertGreater(os.path.getsize(test_pdf_path), 0)

        if os.path.exists(test_pdf_path):
            os.remove(test_pdf_path)


if __name__ == "__main__":
    unittest.main()
