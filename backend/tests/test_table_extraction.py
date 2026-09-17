import os
import sys

# Ensure backend root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest
from app.services.normalization_service import (
    parse_numeric_cell,
    detect_table_unit,
    extract_entity_tuples_from_tables,
    extract_entity_tuples_from_text,
)
from app.services.parsing_service import parse_pdf_document


# ==============================================================================
# 1. UNIT TESTS: NUMERIC PARSING & BOUNDARY BLEED
# ==============================================================================

def test_parse_numeric_cell_clean():
    assert parse_numeric_cell("7.07") == 7.07
    assert parse_numeric_cell("85.81") == 85.81
    assert parse_numeric_cell("118.54") == 118.54
    assert parse_numeric_cell("1,047.68") == 1047.68
    assert parse_numeric_cell("0.00") == 0.0


def test_parse_numeric_cell_leading_decimals():
    """TEST C: Verify leading-decimal numbers (.03, .00) and standard decimals."""
    assert parse_numeric_cell(".03") == 0.03
    assert parse_numeric_cell(".00") == 0.0
    assert parse_numeric_cell("0.03") == 0.03
    assert parse_numeric_cell("7.07") == 7.07


def test_parse_numeric_cell_boundary_bleed():
    """Verifies that adjacent percentage/achievement numbers bleeding into the cell are safely isolated."""
    assert parse_numeric_cell("7.07 1") == 7.07
    assert parse_numeric_cell("4.33 9") == 4.33
    assert parse_numeric_cell("11.70 8") == 11.70
    assert parse_numeric_cell("85.81 9") == 85.81
    assert parse_numeric_cell("118.54 1") == 118.54
    assert parse_numeric_cell("0.00 0") == 0.0


def test_parse_numeric_cell_with_symbols_and_nulls():
    assert parse_numeric_cell("▲ 12.43") == 12.43
    assert parse_numeric_cell("▼ 7.53") == 7.53
    assert parse_numeric_cell("-") is None
    assert parse_numeric_cell("--") is None
    assert parse_numeric_cell("N/A") is None
    assert parse_numeric_cell(None) is None
    assert parse_numeric_cell("") is None


# ==============================================================================
# 2. UNIT TESTS: HEADER-LEVEL UNIT PROPAGATION
# ==============================================================================

def test_detect_table_unit_propagation():
    # Test Fig. in MT
    rows_mt = [["Sl No", "Subs", "Monthly Target", "Production during Mar"], ["", "", "", "FY 25"]]
    assert detect_table_unit(rows_mt, "Table 1.1 Coal Production Fig. in MT") == "MT"
    assert detect_table_unit(rows_mt, "(Qty. in MT)") == "MT"

    # Test M.Cu.M
    rows_mcum = [["Sl No", "Subs", "OBR Target", "OBR during Mar"]]
    assert detect_table_unit(rows_mcum, "Table 1.2 Overburden Removal Fig. in M.Cu.M") == "M.Cu.M"

    # Default fallback
    assert detect_table_unit(rows_mt, "Table 1.1 Coal Production") == "MT"


# ==============================================================================
# 3. STRUCTURED FIXTURE TESTS: MARCH 2025 TABLE 1.1
# ==============================================================================

MARCH_2025_TABLE_ROWS = [
    ["Sl No", "Subs", "Monthly Target", "Production during Mar", "", "", "", "Production upto Mar", "", ""],
    ["", "", "", "FY 25", "Achmt.(%)", "FY 24", "Growth (%) M-o-M", "FY 25", "FY 24", "Growth (%) Y-o-Y"],
    ["1", "ECL", "6.60", "7.07 1", "06.98", "6.93", "▲ 2.01", "52.04", "47.56", "▲ 9.41"],
    ["2", "BCCL", "4.55", "4.33 9", "5.19", "3.86", "▲ 12.20", "40.50", "41.10", "▼ 1.45"],
    ["3", "CCL", "13.08", "11.70 8", "9.48", "12.23", "▼ 4.33", "87.54", "86.06", "▲ 1.73"],
    ["4", "NCL", "11.67", "10.87 9", "3.17", "10.19", "▲ 6.69", "139.00", "136.15", "▲ 2.09"],
    ["5", "WCL", "9.20", "8.76 9", "5.27", "9.04", "▼ 3.07", "69.12", "69.11", "▲ 0.01"],
    ["6", "SECL", "26.40", "20.93 7", "9.28", "25.11", "▼ 16.66", "167.50", "187.38", "▼ 10.61"],
    ["7", "MCL", "22.80", "22.15 9", "7.11", "21.20", "▲ 4.45", "225.17", "206.09", "▲ 9.26"],
    ["8", "NEC", "0.03", "0.00 0", ".00", "0.02", "▼ 100.00", "0.20", "0.20", "▲ 0.00"],
    ["CIL", "", "94.33", "85.81 9", "0.96", "88.58", "▼ 3.13", "781.08", "773.65", "▲ 0.96"],
    ["9", "SCCL", "7.14", "8.91 1", "24.82", "7.30", "▲ 22.08", "69.01", "70.02", "▼ 1.45"],
    ["10", "Captive/Others", "14.22", "23.82 1", "67.50", "20.80", "▲ 14.53", "197.60", "154.16", "▲ 28.18"],
    ["Grand Total", "", "115.69", "118.54 1", "02.46", "116.68", "▲ 1.59", "1047.68", "997.83", "▲ 5.00"],
]


def test_extract_march_2025_table():
    tables = [{
        "table_index": 0,
        "bbox": [52.14, 261.66, 611.10, 459.42],
        "row_count": 14,
        "col_count": 10,
        "raw_rows": MARCH_2025_TABLE_ROWS
    }]
    page_text = "Table 1.1: Coal Production Fig. in MT Coal Production during FY 2024-25"

    metrics = extract_entity_tuples_from_tables(
        tables=tables,
        page_number=5,
        page_text=page_text,
        default_subsidiary="CIL HQ",
        default_year="2024-25"
    )

    # Group monthly metrics by entity
    monthly_metrics = {m["mine_name"]: m for m in metrics if m["metric_name"] == "Coal Production"}
    cumulative_metrics = {m["mine_name"]: m for m in metrics if m["metric_name"] == "Cumulative Coal Production"}

    # Verify all 12 corporate entities in monthly production
    assert monthly_metrics["ECL"]["numeric_value"] == 7.07
    assert monthly_metrics["ECL"]["unit"] == "MT"
    assert monthly_metrics["ECL"]["standard_unit"] == "MT"
    assert monthly_metrics["ECL"]["subsidiary"] == "ECL"

    assert monthly_metrics["BCCL"]["numeric_value"] == 4.33
    assert monthly_metrics["CCL"]["numeric_value"] == 11.70
    assert monthly_metrics["NCL"]["numeric_value"] == 10.87
    assert monthly_metrics["WCL"]["numeric_value"] == 8.76
    assert monthly_metrics["SECL"]["numeric_value"] == 20.93
    assert monthly_metrics["MCL"]["numeric_value"] == 22.15
    assert monthly_metrics["NEC"]["numeric_value"] == 0.00

    assert monthly_metrics["CIL Total"]["numeric_value"] == 85.81
    assert monthly_metrics["CIL Total"]["subsidiary"] is None

    assert monthly_metrics["SCCL"]["numeric_value"] == 8.91
    assert monthly_metrics["Captive/Others"]["numeric_value"] == 23.82
    assert monthly_metrics["Captive/Others"]["subsidiary"] is None

    assert monthly_metrics["Grand Total"]["numeric_value"] == 118.54
    assert monthly_metrics["Grand Total"]["subsidiary"] is None

    # Verify cumulative values are distinguished from monthly values
    assert cumulative_metrics["ECL"]["numeric_value"] == 52.04
    assert cumulative_metrics["CIL Total"]["numeric_value"] == 781.08
    assert cumulative_metrics["Grand Total"]["numeric_value"] == 1047.68


# ==============================================================================
# 4. STRUCTURED FIXTURE TESTS: NOVEMBER 2024 TABLE 1.1
# ==============================================================================

NOVEMBER_2024_TABLE_ROWS = [
    ["Sl No", "Subs", "Monthly Target", "Production during Nov", "", "", "", "Production upto Nov", "", ""],
    ["", "", "", "FY 25", "Achmt.(%)", "FY 24", "Growth (%) M-o-M", "FY 25", "FY 24", "Growth (%) Y-o-Y"],
    ["1", "ECL", "5.06", "4.59", "90.65", "4.08", "▲ 12.43", "28.76", "25.39", "▲ 13.27"],
    ["2", "BCCL", "3.86", "3.42", "88.70", "3.70", "▼ 7.53", "25.52", "26.20", "▼ 2.61"],
    ["3", "CCL", "8.72", "7.29", "83.60", "7.20", "▲ 1.26", "49.66", "47.84", "▲ 3.80"],
    ["4", "NCL", "11.95", "12.78", "106.95", "11.95", "▲ 6.98", "92.20", "92.10", "▲ 0.11"],
    ["5", "WCL", "6.12", "6.26", "102.39", "6.16", "▲ 1.69", "37.99", "36.56", "▲ 3.90"],
    ["6", "SECL", "16.50", "13.31", "80.65", "14.76", "▼ 9.86", "97.21", "106.51", "▼ 8.73"],
    ["7", "MCL", "19.85", "19.50", "98.24", "18.15", "▲ 7.46", "139.51", "125.30", "▲ 11.34"],
    ["8", "NEC", "0.03", "0.03", "104.00", "0.03", "▼ 10.34", "0.15", "0.10", "▲ 55.21"],
    ["CIL", "", "72.08", "67.18", "93.20", "66.03", "▲ 1.74", "470.98", "460.00", "▲ 2.39"],
    ["9", "SCCL", "6.66", "6.31", "94.76", "6.08", "▲ 3.73", "40.15", "43.19", "▼ 7.03"],
    ["10", "Captive/Others", "14.51", "17.32", "119.35", "12.45", "▲ 39.13", "117.23", "88.14", "▲ 33.01"],
    ["Grand Total", "", "93.25", "90.80", "97.38", "84.56", "▲ 7.39", "628.37", "591.33", "▲ 6.26"],
]


def test_extract_november_2024_table():
    tables = [{
        "table_index": 0,
        "bbox": [52.14, 261.66, 611.10, 459.42],
        "row_count": 14,
        "col_count": 10,
        "raw_rows": NOVEMBER_2024_TABLE_ROWS
    }]
    page_text = "Table 1.1: Coal Production Fig. in MT Coal Production during Nov 2024 FY 25"

    metrics = extract_entity_tuples_from_tables(
        tables=tables,
        page_number=5,
        page_text=page_text,
        default_subsidiary="CIL HQ",
        default_year="2024-25"
    )

    monthly_metrics = {m["mine_name"]: m for m in metrics if m["metric_name"] == "Coal Production"}

    assert monthly_metrics["CIL Total"]["numeric_value"] == 67.18
    assert monthly_metrics["Grand Total"]["numeric_value"] == 90.80
    assert monthly_metrics["ECL"]["numeric_value"] == 4.59
    assert monthly_metrics["SECL"]["numeric_value"] == 13.31


# ==============================================================================
# 5. REAL PDF INTEGRATION TEST (READ-ONLY)
# ==============================================================================

def test_real_pdf_march_2025_page_5():
    pdf_path = r"C:\Users\Henil Patel\Downloads\srn-march-2025.pdf"
    if not os.path.exists(pdf_path):
        pytest.skip(f"Local test PDF not found at {pdf_path}")

    pages = parse_pdf_document(pdf_path)
    page_5 = next((p for p in pages if p["page_number"] == 5), None)
    assert page_5 is not None, "Page 5 not found in parsed document"
    assert "tables" in page_5, "'tables' key must exist in page dict"
    assert len(page_5["tables"]) >= 1, "Page 5 must contain at least 1 extracted table"

    metrics = extract_entity_tuples_from_tables(
        tables=page_5["tables"],
        page_number=5,
        page_text=page_5["text"],
        default_subsidiary="CIL HQ",
        default_year="2024-25"
    )

    monthly_metrics = {m["mine_name"]: m for m in metrics if m["metric_name"] == "Coal Production"}

    # Authoritative Ministry figures verification
    expected_values = {
        "ECL": 7.07,
        "BCCL": 4.33,
        "CCL": 11.70,
        "NCL": 10.87,
        "WCL": 8.76,
        "SECL": 20.93,
        "MCL": 22.15,
        "NEC": 0.00,
        "CIL Total": 85.81,
        "SCCL": 8.91,
        "Captive/Others": 23.82,
        "Grand Total": 118.54,
    }

    for entity, exp_val in expected_values.items():
        assert entity in monthly_metrics, f"Missing entity '{entity}' in extracted monthly metrics"
        assert monthly_metrics[entity]["numeric_value"] == exp_val, (
            f"Entity '{entity}' expected {exp_val} MT, got {monthly_metrics[entity]['numeric_value']} MT"
        )
        assert monthly_metrics[entity]["unit"] == "MT"


def test_real_pdf_november_2024_page_5():
    pdf_path = r"C:\Users\Henil Patel\Downloads\srn-nov-2024.pdf"
    if not os.path.exists(pdf_path):
        pytest.skip(f"Local test PDF not found at {pdf_path}")

    pages = parse_pdf_document(pdf_path)
    page_5 = next((p for p in pages if p["page_number"] == 5), None)
    assert page_5 is not None, "Page 5 not found in parsed document"
    assert "tables" in page_5, "'tables' key must exist in page dict"
    assert len(page_5["tables"]) >= 1, "Page 5 must contain at least 1 extracted table"

    metrics = extract_entity_tuples_from_tables(
        tables=page_5["tables"],
        page_number=5,
        page_text=page_5["text"],
        default_subsidiary="CIL HQ",
        default_year="2024-25"
    )

    monthly_metrics = {m["mine_name"]: m for m in metrics if m["metric_name"] == "Coal Production"}

    expected_nov_values = {
        "ECL": 4.59,
        "BCCL": 3.42,
        "CCL": 7.29,
        "NCL": 12.78,
        "WCL": 6.26,
        "SECL": 13.31,
        "MCL": 19.50,
        "NEC": 0.03,
        "CIL Total": 67.18,
        "SCCL": 6.31,
        "Captive/Others": 17.32,
        "Grand Total": 90.80,
    }

    for entity, exp_val in expected_nov_values.items():
        assert entity in monthly_metrics, f"Missing entity '{entity}' in November 2024 monthly metrics"
        assert monthly_metrics[entity]["numeric_value"] == exp_val, (
            f"Entity '{entity}' expected {exp_val} MT, got {monthly_metrics[entity]['numeric_value']} MT"
        )
    assert monthly_metrics["CIL Total"]["unit"] == "MT"


# ==============================================================================
# 6. REGRESSION TESTS: EXISTING NON-TABLE TEXT EXTRACTION
# ==============================================================================

def test_existing_text_extraction_regression():
    sample_text = (
        "Eastern Coalfields Limited achieved total coal production of 42.50 Lakh Tonnes in FY 2023-24."
    )
    metrics = extract_entity_tuples_from_text(
        text=sample_text,
        page_number=1,
        default_subsidiary="ECL",
        default_year="2023-24"
    )
    assert len(metrics) >= 1
    prod_m = next((m for m in metrics if m["metric_name"] == "Coal Production"), None)
    assert prod_m is not None
    assert prod_m["numeric_value"] == 42.50
    assert prod_m["unit"] == "Lakh Tonnes"
    assert prod_m["standard_value"] == 4.25
    assert prod_m["standard_unit"] == "MT"


# ==============================================================================
# 7. REGRESSION TESTS: PR #51 HARDENED TABLE EXTRACTION (TEST A & TEST B)
# ==============================================================================

def test_non_production_table_fallback_safety():
    """TEST A: Verify a non-production table (e.g. Overburden Removal) with >=4 columns
    does NOT manufacture 'Coal Production' metrics via column-3 fallback."""
    obr_table_rows = [
        ["Sl No", "Subsidiary", "OBR Target", "OBR Achievement", "Growth %"],
        ["1", "ECL", "10.50", "12.30", "17.14"],
        ["2", "BCCL", "8.20", "7.90", "-3.65"],
        ["3", "CIL Total", "85.00", "88.20", "3.76"],
    ]
    page_text = "Table 1.2: Overburden Removal\nFig. in M.Cu.M\nPerformance of OBR during March 2025."

    metrics = extract_entity_tuples_from_tables(
        tables=[{"raw_rows": obr_table_rows}],
        page_number=6,
        page_text=page_text,
        default_subsidiary="CIL HQ",
        default_year="2024-25"
    )
    # Must NOT produce any Coal Production metric
    coal_prod_metrics = [m for m in metrics if m["metric_name"] == "Coal Production"]
    assert len(coal_prod_metrics) == 0, f"Expected 0 Coal Production metrics from OBR table, got: {coal_prod_metrics}"


def test_aggregate_rows_not_treated_as_operating_subsidiaries():
    """TEST B: Mock production table containing operating subsidiaries and aggregates.
    Verify operating subsidiaries keep their subsidiary values, while aggregates
    (Grand Total, Captive/Others, CIL Total) have subsidiary=None."""
    mock_rows = [
        ["Sl No", "Company", "Target", "Production during Mar FY 25", "Growth %"],
        ["1", "ECL", "6.50", "7.07", "8.8"],
        ["2", "BCCL", "4.00", "4.33", "8.2"],
        ["3", "CIL Total", "80.00", "85.81", "7.3"],
        ["4", "Captive/Others", "20.00", "23.82", "19.1"],
        ["5", "Grand Total", "105.00", "118.54", "12.9"],
    ]
    page_text = "Table 1.1: Coal Production\nFig. in MT\nMarch 2025."

    metrics = extract_entity_tuples_from_tables(
        tables=[{"raw_rows": mock_rows}],
        page_number=5,
        page_text=page_text,
        default_subsidiary="CIL HQ",
        default_year="2024-25"
    )
    monthly_metrics = {m["mine_name"]: m for m in metrics if m["metric_name"] == "Coal Production"}

    # Operating subsidiaries
    assert monthly_metrics["ECL"]["subsidiary"] == "ECL"
    assert monthly_metrics["BCCL"]["subsidiary"] == "BCCL"

    # Aggregates must NOT be treated as operating CIL subsidiaries
    assert monthly_metrics["CIL Total"]["subsidiary"] is None
    assert monthly_metrics["Captive/Others"]["subsidiary"] is None
    assert monthly_metrics["Grand Total"]["subsidiary"] is None

    # Entity/mine labels must be preserved
    assert monthly_metrics["CIL Total"]["mine_name"] == "CIL Total"
    assert monthly_metrics["Captive/Others"]["mine_name"] == "Captive/Others"
    assert monthly_metrics["Grand Total"]["mine_name"] == "Grand Total"

