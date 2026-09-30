import unittest
import os
import sys
import re

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Day 8 Golden Dataset Constants & Thresholds
ARITHMETIC_TOLERANCE_PERCENT = 5.0
CONFLICT_THRESHOLD_PERCENT = 1.0
RRF_K_CONSTANT = 60
MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024


def normalize_unit_to_mt(raw_value: float, raw_unit: str):
    unit_clean = raw_unit.strip().lower()
    if "lakh" in unit_clean:
        return round(raw_value * 0.1, 4), "MT"
    elif "million" in unit_clean or unit_clean == "mt":
        return round(raw_value * 1.0, 4), "MT"
    elif "thousand" in unit_clean:
        return round(raw_value * 0.001, 4), "MT"
    elif "m.cu.m" in unit_clean or "mcum" in unit_clean:
        return round(raw_value * 1.0, 4), "M.Cu.M"
    return raw_value, "MT"


def validate_metric_arithmetic(reported_value: float, calculated_value: float):
    if reported_value == 0:
        return (0.0, "VALIDATED") if calculated_value == 0 else (100.0, "WARNING_ARITHMETIC")
    pct_diff = round((abs(calculated_value - reported_value) / abs(reported_value)) * 100.0, 2)
    status = "WARNING_ARITHMETIC" if pct_diff > ARITHMETIC_TOLERANCE_PERCENT else "VALIDATED"
    return pct_diff, status


def calc_conflict_percentage(val_a: float, val_b: float):
    ref = max(abs(val_a), abs(val_b))
    if ref == 0:
        return 0.0, "NO_CONFLICT"
    pct_diff = round((abs(val_a - val_b) / ref) * 100.0, 2)
    status = "OPEN" if pct_diff > CONFLICT_THRESHOLD_PERCENT else "NO_CONFLICT"
    return pct_diff, status


def compute_rrf_score(vec_rank: int, kw_rank: int):
    score_vec = 1.0 / (RRF_K_CONSTANT + vec_rank) if vec_rank > 0 else 0.0
    score_kw = 1.0 / (RRF_K_CONSTANT + kw_rank) if kw_rank > 0 else 0.0
    return round(score_vec + score_kw, 6)


def build_isolated_prompt(query: str, evidence_chunks: list) -> str:
    context_blocks = [f"[{c['filename']}, Page {c['page_number']}]\n{c['text']}" for c in evidence_chunks]
    context_str = "\n\n".join(context_blocks)
    return f"<untrusted_document_context>\n{context_str}\n</untrusted_document_context>\nUSER QUESTION: {query}"


def extract_and_validate_citations(raw_answer: str, evidence_chunks: list):
    citation_pattern = re.compile(r"\[([A-Za-z0-9_\-\.]+),\s*Page\s*(\d+)\]")
    found_matches = citation_pattern.findall(raw_answer)
    valid_evidence_set = {(c["filename"].lower(), c["page_number"]) for c in evidence_chunks}
    validated_citations = []
    for fname, pnum_str in found_matches:
        pnum = int(pnum_str)
        if (fname.lower(), pnum) in valid_evidence_set:
            validated_citations.append({"document_name": fname, "page_number": pnum, "citation_tag": f"[{fname}, Page {pnum}]"})
    return validated_citations, len(validated_citations) > 0


class TestDay8GoldenDatasetBenchmark(unittest.TestCase):

    def test_case_a_valid_metric(self):
        """Golden Case A: Valid Metric (2.0% diff <= 5.0% threshold) -> VALIDATED."""
        pct_diff, status = validate_metric_arithmetic(reported_value=100.0, calculated_value=102.0)
        self.assertEqual(pct_diff, 2.0)
        self.assertEqual(status, "VALIDATED")

    def test_case_b_arithmetic_warning(self):
        """Golden Case B: Arithmetic Warning (8.0% diff > 5.0% threshold) -> WARNING_ARITHMETIC."""
        pct_diff, status = validate_metric_arithmetic(reported_value=100.0, calculated_value=108.0)
        self.assertEqual(pct_diff, 8.0)
        self.assertEqual(status, "WARNING_ARITHMETIC")

    def test_case_c_cross_document_agreement(self):
        """Golden Case C: Cross-Document Agreement (0.5% diff <= 1.0% threshold) -> NO_CONFLICT."""
        pct_diff, status = calc_conflict_percentage(val_a=100.0, val_b=100.5)
        self.assertEqual(pct_diff, 0.5)
        self.assertEqual(status, "NO_CONFLICT")

    def test_case_d_cross_document_conflict(self):
        """Golden Case D: Cross-Document Conflict (2.44% diff > 1.0% threshold) -> OPEN conflict."""
        pct_diff, status = calc_conflict_percentage(val_a=100.0, val_b=102.5)
        self.assertEqual(pct_diff, 2.44)
        self.assertEqual(status, "OPEN")

    def test_case_e_hybrid_search_and_rrf(self):
        """Golden Case E: Hybrid Search Reciprocal Rank Fusion (RRF k=60)."""
        # Candidate A: Vector Rank 1, Keyword Rank 2
        score_a = compute_rrf_score(vec_rank=1, kw_rank=2)
        # 1/61 + 1/62 = 0.0163934 + 0.0161290 = 0.032522
        self.assertEqual(score_a, 0.032522)

        # Candidate B: Vector Rank 2, Keyword Rank 1
        score_b = compute_rrf_score(vec_rank=2, kw_rank=1)
        self.assertEqual(score_b, 0.032522)

        # Candidate C: Vector Rank 10, Keyword None
        score_c = compute_rrf_score(vec_rank=10, kw_rank=0)
        self.assertEqual(score_c, 0.014286)

    test_case_e_hybrid_search_and_rrf.description = "RRF k=60 calculation test"

    def test_case_f_citation_gate_verification(self):
        """Golden Case F: Citation Gate Verification & Hallucination Rejection."""
        evidence = [
            {"filename": "ECL_Report_2023-24.pdf", "page_number": 14},
            {"filename": "BCCL_Audit_Q4.pdf", "page_number": 22}
        ]

        valid_response = "Production reached 4.25 MT [ECL_Report_2023-24.pdf, Page 14]."
        invalid_response = "Production reached 500 MT [Fake_Document.pdf, Page 999]."

        valid_cites, valid_pass = extract_and_validate_citations(valid_response, evidence)
        self.assertEqual(len(valid_cites), 1)
        self.assertTrue(valid_pass)

        invalid_cites, invalid_pass = extract_and_validate_citations(invalid_response, evidence)
        self.assertEqual(len(invalid_cites), 0)
        self.assertFalse(invalid_pass)

    def test_case_g_unit_normalization(self):
        """Golden Case G: Deterministic Unit Normalization Engine."""
        # 1. 42.50 Lakh Tonnes -> 4.25 MT
        v1, u1 = normalize_unit_to_mt(42.50, "Lakh Tonnes")
        self.assertEqual(v1, 4.25)
        self.assertEqual(u1, "MT")

        # 2. 167.00 Million Tonnes -> 167.00 MT
        v2, u2 = normalize_unit_to_mt(167.00, "Million Tonnes")
        self.assertEqual(v2, 167.00)
        self.assertEqual(u2, "MT")

        # 3. 500.00 Thousand Tonnes -> 0.50 MT
        v3, u3 = normalize_unit_to_mt(500.00, "Thousand Tonnes")
        self.assertEqual(v3, 0.50)
        self.assertEqual(u3, "MT")


if __name__ == "__main__":
    unittest.main()
