"""Regression coverage for chart/table separation in native PDF extraction."""

import os
import sys

import fitz

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.parsing_service import parse_pdf_result


def _chart_and_table_pdf() -> bytes:
    document = fitz.open()
    page = document.new_page(width=900, height=650)

    # A vector bar chart with category labels and numeric annotations.  Its
    # axes/bars are intentionally drawable so the regression exercises the
    # same native false-table shape produced by PyMuPDF on chart regions.
    categories = ["NLCIL", "GMDCL", "GIPCL", "RSMML", "BLMCL", "GHCL", "VS Lignite"]
    production = [120, 180, 95, 150, 110, 135, 165]
    page.insert_text((260, 40), "Production and Dispatch", fontsize=14)
    page.draw_line((70, 500), (800, 500))
    page.draw_line((70, 100), (70, 500))
    for y in (150, 250, 350, 450):
        page.draw_line((70, y), (800, y), color=(0.7, 0.7, 0.7))
    for index, (category, value) in enumerate(zip(categories, production)):
        x = 100 + index * 85
        page.draw_rect(fitz.Rect(x, 500 - value, x + 32, 500), color=(0.1, 0.3, 0.8), fill=(0.3, 0.5, 0.8))
        page.draw_rect(fitz.Rect(x + 36, 500 - value * 0.8, x + 68, 500), color=(0.8, 0.3, 0.2), fill=(0.8, 0.5, 0.4))
        page.insert_text((x, 525), category, fontsize=8)
        page.insert_text((x + 2, 490 - value), str(value), fontsize=8)
        page.insert_text((x + 37, 490 - int(value * 0.8)), str(round(value * 0.8, 1)), fontsize=8)

    # A genuine bordered table on the same page must remain a table.
    page.draw_rect(fitz.Rect(40, 575, 340, 635), color=(0, 0, 0))
    page.draw_line((180, 575), (180, 635))
    page.draw_line((260, 575), (260, 635))
    page.draw_line((40, 605), (340, 605))
    page.insert_text((45, 598), "Production")
    page.insert_text((185, 598), "781.05")
    page.insert_text((265, 598), "781.50")
    page.insert_text((45, 628), "Dispatch")
    page.insert_text((185, 628), "0.781")
    page.insert_text((265, 628), "78.105")

    raw = document.tobytes()
    document.close()
    return raw


def test_vector_bar_chart_is_rejected_but_real_table_is_persisted():
    result = parse_pdf_result("", _chart_and_table_pdf(), filename="chart-and-table.pdf")

    assert len(result.tables) == 1
    table = result.tables[0]
    assert table.table_number == 1
    assert table.rows == [["Dispatch", "0.781", "78.105"]]
    assert table.headers == ["Production", "781.05", "781.50"]
    assert all(category not in {cell["value"] for cell in table.cells} for category in [
        "NLCIL", "GMDCL", "GIPCL", "RSMML", "BLMCL", "GHCL", "VS Lignite",
    ])

    rejection = result.pages[0].metadata["rejected_table_candidates"]
    assert len(rejection) == 1
    assert rejection[0]["classification"] == "FIGURE_OR_CHART"
    assert rejection[0]["bounding_box"] is not None
    assert rejection[0]["filled_vector_region_count"] >= 3
    assert any("likely figure/chart" in warning for warning in result.warnings)

    # The source text remains available in native page evidence even though
    # chart labels/numbers are not fabricated into table cells.
    assert "NLCIL" in result.pages[0].text
    assert "Production and Dispatch" in result.pages[0].text
