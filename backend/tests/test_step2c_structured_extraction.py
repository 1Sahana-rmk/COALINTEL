from pathlib import Path
import sys
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app.models  # noqa: F401 - register all models before create_all
from app.models.document import Document
from app.models.structured_fact import StructuredFact
from app.api.documents import get_document_structured_facts
from app.services.document_models import DocumentResult, EvidenceBlock, PageResult, TableResult
from app.services.structured_extraction_service import (
    extract_structured_fact_candidates,
    persist_structured_fact_candidates,
    resolve_metric,
    validate_ai_fact_proposal,
)
from app.services.storage_service import save_uploaded_file, delete_uploaded_file
from database import Base


def _period_table_result():
    return DocumentResult(
        document_id=7,
        filename="period-table.pdf",
        file_type="PDF",
        pages=[PageResult(page_number=1, text="MCL Coal Production Apr 2023 781.05 MT")],
        tables=[
            TableResult(
                page_number=1,
                table_number=1,
                title="Monthly coal production",
                headers=[
                    "Mine",
                    "Coal Production Apr 2023 (MT)",
                    "Coal Production May 2023 (MT)",
                ],
                rows=[["MCL", "781.05", "1,294.73"]],
                bounding_box=[10, 20, 500, 300],
                extraction_confidence=0.96,
                extraction_method="NATIVE",
                cells=[
                    {"row_index": 1, "column_index": 0, "value": "MCL", "bounding_box": [10, 40, 90, 60]},
                    {"row_index": 1, "column_index": 1, "value": 781.05, "bounding_box": [100, 40, 220, 60]},
                    {"row_index": 1, "column_index": 2, "value": 1294.73, "bounding_box": [230, 40, 360, 60]},
                ],
            )
        ],
    )


def test_table_facts_keep_period_and_cell_provenance():
    facts = extract_structured_fact_candidates(_period_table_result(), document_id=7)
    table_facts = [fact for fact in facts if fact.evidence_type == "TABLE_CELL"]

    april = next(fact for fact in table_facts if fact.raw_value_text == "781.05")
    may = next(fact for fact in table_facts if fact.raw_value_text == "1,294.73")

    assert april.metric_type == "COAL_PRODUCTION"
    assert april.period_normalized == "April 2023"
    assert may.period_normalized == "May 2023"
    assert april.raw_value_numeric == pytest.approx(781.05)
    assert may.raw_value_numeric == pytest.approx(1294.73)
    assert april.raw_unit == "MT"
    assert april.evidence_locator["table_number"] == 1
    assert april.evidence_locator["row_index"] == 1
    assert april.evidence_locator["column_index"] == 1
    assert april.evidence_locator["bounding_box"] == [100, 40, 220, 60]
    assert april.validation_status == "ACCEPTED"


def test_ai_proposal_must_be_proven_by_supplied_table_evidence():
    result = _period_table_result()
    supported = validate_ai_fact_proposal(
        {
            "page_number": 1,
            "entity_name_raw": "MCL",
            "metric_name_raw": "Coal Production Apr 2023",
            "raw_value_text": "781.05",
            "raw_unit": "MT",
            "period_raw": "Apr 2023",
            "evidence_type": "TABLE_CELL",
            "evidence_locator": {"table_number": 1, "row_index": 1, "column_index": 1},
        },
        result,
    )
    unsupported = validate_ai_fact_proposal(
        {
            "page_number": 1,
            "entity_name_raw": "MCL",
            "metric_name_raw": "Coal Production Apr 2023",
            "raw_value_text": "999.99",
            "raw_unit": "MT",
            "period_raw": "Apr 2023",
            "evidence_type": "TABLE_CELL",
            "evidence_locator": {"table_number": 1, "row_index": 1, "column_index": 1},
        },
        result,
    )
    assert supported["accepted"] is True
    assert unsupported["accepted"] is False
    assert any("located" in warning for warning in unsupported["warnings"])


def test_structural_row_labels_are_not_canonical_entities_and_numbers_are_safe():
    result = DocumentResult(
        document_id=8,
        filename="safety.pdf",
        file_type="PDF",
        pages=[
            PageResult(
                page_number=3,
                text=(
                    "COAL PRODUCTION TEST\n"
                    "BCCL Production: 781.05 MT\n"
                    "ECL Production: 1,294.73 MT\n"
                    "Difference: -14.82 MT\n"
                    "Efficiency: 97.45%\n"
                    "Borehole: BH-27\n"
                    "Depth: 143.20 m\n"
                    "Thickness: 4.60 m\n"
                    "Grade: G8\n"
                ),
                blocks=[EvidenceBlock(text="Efficiency: 97.45%", bbox=[1, 2, 3, 4], confidence=0.81)],
                confidence=0.81,
                extraction_method="OCR",
                metadata={"ocr_engine": "tesseract"},
            )
        ],
        tables=[
            TableResult(
                page_number=3,
                table_number=2,
                headers=["Sl No", "Mine", "Coal Production (MT)"],
                rows=[["1", "Sl No", "781.05"]],
                extraction_confidence=0.55,
                extraction_method="OCR",
            )
        ],
    )
    facts = extract_structured_fact_candidates(result, document_id=8)

    assert any(fact.raw_value_text == "781.05" for fact in facts)
    assert any(fact.raw_value_text == "1,294.73" for fact in facts)
    assert any(fact.raw_value_text == "-14.82" for fact in facts)
    assert any(fact.raw_value_text == "97.45" and fact.raw_unit == "%" for fact in facts)
    assert any(fact.raw_value_text == "143.20" and fact.raw_unit == "m" for fact in facts)
    assert any(fact.raw_value_text == "4.60" and fact.raw_unit == "m" for fact in facts)
    assert any(fact.raw_value_text == "143.20" and fact.normalized_unit == "m" for fact in facts)
    assert any(fact.raw_value_text == "BH-27" and fact.metric_type == "BOREHOLE_ID" for fact in facts)

    structural = [fact for fact in facts if fact.evidence_type == "TABLE_CELL" and fact.raw_value_text == "781.05"]
    assert structural
    assert structural[0].entity_type == "STRUCTURAL"
    assert structural[0].entity_name_canonical is None
    assert structural[0].validation_status == "REVIEW_REQUIRED"


def test_serial_number_columns_are_not_emitted_as_structured_facts():
    result = DocumentResult(
        document_id=12,
        filename="serial-column.pdf",
        file_type="PDF",
        pages=[PageResult(page_number=1, text="Production table")],
        tables=[
            TableResult(
                page_number=1,
                table_number=1,
                headers=["Sl. No.", "Mine", "Coal Production (MT)"],
                rows=[["1", "MCL", "781.05"]],
                extraction_confidence=0.95,
                extraction_method="NATIVE_TABLE",
            )
        ],
    )

    facts = extract_structured_fact_candidates(result, document_id=12)
    table_facts = [fact for fact in facts if fact.evidence_type == "TABLE_CELL"]

    assert not any(fact.raw_value_text == "1" for fact in table_facts)
    production = next(fact for fact in table_facts if fact.raw_value_text == "781.05")
    assert production.metric_type == "COAL_PRODUCTION"
    assert production.evidence_locator["column_index"] == 2


def test_period_label_cells_are_not_numeric_measurements():
    result = DocumentResult(
        document_id=13,
        filename="period-label-cell.pdf",
        file_type="PDF",
        pages=[PageResult(page_number=1, text="Dispatch table")],
        tables=[
            TableResult(
                page_number=1,
                table_number=1,
                headers=["Entity", "Progressive Dispatch", "Production"],
                rows=[["MCL", "FY 21", "12.50"]],
                extraction_confidence=0.90,
                extraction_method="NATIVE_TABLE",
            )
        ],
    )

    facts = extract_structured_fact_candidates(result, document_id=13)
    table_facts = [fact for fact in facts if fact.evidence_type == "TABLE_CELL"]

    assert not any(fact.raw_value_text == "21" for fact in table_facts)
    assert any(fact.raw_value_text == "12.50" for fact in table_facts)


def test_numbered_section_labels_are_not_numeric_measurements():
    result = DocumentResult(
        document_id=14,
        filename="numbered-section-label.pdf",
        file_type="PDF",
        pages=[PageResult(page_number=1, text="Exploration table")],
        tables=[
            TableResult(
                page_number=1,
                table_number=1,
                headers=["ITEM", "Current Month", "Growth"],
                rows=[["1. DRILLING BY CMPDI (DEPARTMENT (in metre)", "400", "10%"]],
                extraction_confidence=0.90,
                extraction_method="NATIVE_TABLE",
            )
        ],
    )

    facts = extract_structured_fact_candidates(result, document_id=14)
    table_facts = [fact for fact in facts if fact.evidence_type == "TABLE_CELL"]

    assert not any(fact.raw_value_text == "1" for fact in table_facts)
    current = next(fact for fact in table_facts if fact.raw_value_text == "400")
    assert current.raw_unit is None
    assert any(fact.raw_value_text == "10" and fact.raw_unit == "%" for fact in table_facts)


def test_specific_table_header_overrides_broad_row_metric_context():
    metric, method, confidence = resolve_metric(
        "DRILLING Growth over corresponding month of 2019-20 -8%",
        "Growth over corresponding month of 2019-20",
    )
    assert metric == "GROWTH_PERCENT"
    assert method == "HEADER_RULE"
    assert confidence == pytest.approx(0.95)


def test_navigation_toc_rows_are_not_measurement_facts_but_genuine_table_survives():
    result = DocumentResult(
        document_id=9,
        filename="contents-and-data.pdf",
        file_type="PDF",
        pages=[PageResult(page_number=7, text="Contents")],
        tables=[
            TableResult(
                page_number=7,
                table_number=1,
                headers=["Chapter Name", "Table", "Page"],
                rows=[
                    ["All India Summary", "Summary of Coal Production", "1"],
                    ["", "State-wise Coal Production", "3"],
                    ["", "Sector-wise Coal Despatch", "4"],
                    ["Exploration", "Drilling Performance", "42"],
                    ["", "OBR Status", "48-49"],
                    ["", "Mode-Wise Coal Despatch", "53-55"],
                ],
                extraction_confidence=0.75,
                extraction_method="NATIVE_TABLE",
            ),
            TableResult(
                page_number=7,
                table_number=2,
                headers=["Mine", "Coal Production May 2023 (MT)"],
                rows=[["MCL", "781.05"]],
                extraction_confidence=0.96,
                extraction_method="NATIVE_TABLE",
            ),
        ],
    )
    facts = extract_structured_fact_candidates(result, document_id=9)

    assert not any(fact.evidence_locator.get("table_number") == 1 for fact in facts)
    genuine = [fact for fact in facts if fact.evidence_locator.get("table_number") == 2]
    assert len(genuine) == 1
    assert genuine[0].entity_name_canonical == "MCL"
    assert genuine[0].raw_value_text == "781.05"
    assert genuine[0].period_normalized == "May 2023"


def test_borehole_requires_numeric_identifier_and_context():
    result = DocumentResult(
        document_id=10,
        filename="borehole-context.pdf",
        file_type="PDF",
        pages=[
            PageResult(
                page_number=1,
                text="Office address: Lok Nayak Bhavan\nBorehole ID: BH-27\n",
                extraction_method="NATIVE",
            )
        ],
    )
    facts = extract_structured_fact_candidates(result, document_id=10)
    boreholes = [fact for fact in facts if fact.metric_type == "BOREHOLE_ID"]
    assert len(boreholes) == 1
    assert boreholes[0].raw_value_text == "BH-27"

    false_result = DocumentResult(
        document_id=11,
        filename="ordinary-address.pdf",
        file_type="PDF",
        pages=[PageResult(page_number=1, text="Floor, Lok Nayak Bhavan")],
    )
    assert not any(
        fact.metric_type == "BOREHOLE_ID"
        for fact in extract_structured_fact_candidates(false_result, document_id=11)
    )


def test_fact_keys_are_deterministic_and_persistence_is_idempotent():
    result = _period_table_result()
    first = extract_structured_fact_candidates(result, document_id=7)
    second = extract_structured_fact_candidates(result, document_id=7)
    assert {fact.fact_key for fact in first} == {fact.fact_key for fact in second}
    assert {fact.duplicate_group_key for fact in first} == {fact.duplicate_group_key for fact in second}

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    session.add(
        Document(
            id=7,
            filename="period-table.pdf",
            file_path="uploads/period-table.pdf",
            file_hash="a" * 64,
            file_type="PDF",
        )
    )
    session.commit()

    assert persist_structured_fact_candidates(session, 7, first) == len(first)
    session.commit()
    assert persist_structured_fact_candidates(session, 7, second) == 0
    assert session.query(app.models.StructuredFact).filter_by(document_id=7).count() == len(first)
    response = get_document_structured_facts(7, session, None)
    assert response["count"] == len(first)
    assert response["facts"][0]["evidence_locator"]["table_number"] == 1
    session.close()


def test_common_processing_pipeline_persists_step2c_facts_without_replacing_legacy_metrics():
    from app.services.processing_pipeline import execute_document_processing_pipeline

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    source = b"Mine,Coal Production (MT)\nMCL,781.05\n"
    path = save_uploaded_file(source, "b" * 64, "step2c_pipeline.csv")
    document = Document(
        filename="step2c_pipeline.csv",
        file_path=path,
        file_hash="b" * 64,
        file_type="CSV",
        status="PENDING",
    )
    session.add(document)
    session.commit()
    session.refresh(document)
    try:
        with patch("app.services.processing_pipeline.delete_document_vectors"), patch(
            "app.services.processing_pipeline.add_chunks_to_vector_store", return_value=True
        ):
            assert execute_document_processing_pipeline(session, document.id) is True
        assert session.query(StructuredFact).filter_by(document_id=document.id).count() > 0
        assert document.status == "PARSED"
    finally:
        delete_uploaded_file(path)
        session.close()
