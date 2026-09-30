import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.schemas.validation import ValidationItemResponse
from app.services.validation_service import run_deterministic_validation_feed


class _Query:
    def __init__(self, rows):
        self.rows = rows

    def join(self, *args, **kwargs):
        return self

    def filter(self, *args, **kwargs):
        return self

    def all(self):
        return self.rows


class _Db:
    def __init__(self, rows):
        self.rows = rows

    def query(self, *args, **kwargs):
        return _Query(self.rows)


def test_validation_feed_exposes_extraction_confidence_separately():
    metric = SimpleNamespace(
        id=7,
        document_id=11,
        page_number=4,
        mine_name="ECL",
        subsidiary="ECL",
        metric_name="Coal Production",
        fiscal_year="2023-24",
        standard_value=7.07,
        numeric_value=7.07,
        raw_unit="MT",
        standard_unit="MT",
        validation_status="VALIDATED",
        confidence_score=0.65,
        data_origin="OFFICIAL",
    )

    item = run_deterministic_validation_feed(_Db([(metric, "source.pdf")]))[0]
    response = ValidationItemResponse.model_validate(item)

    assert response.extraction_confidence == 0.65
    assert response.validation_status == "UNVERIFIED"
    assert response.extraction_confidence != 0.95
    assert response.page_number == 4
    assert response.data_origin == "OFFICIAL"


def test_validation_feed_keeps_missing_extraction_confidence_unknown():
    metric = SimpleNamespace(
        id=8,
        document_id=12,
        page_number=1,
        mine_name="Unspecified Mine",
        subsidiary="CIL HQ",
        metric_name="Mining Metric (Unclassified)",
        fiscal_year="2023-24",
        standard_value=1.0,
        numeric_value=1.0,
        raw_unit="MT",
        standard_unit="MT",
        validation_status="UNVERIFIED",
        confidence_score=None,
        data_origin="UNKNOWN",
    )

    item = run_deterministic_validation_feed(_Db([(metric, "source.pdf")]))[0]
    response = ValidationItemResponse.model_validate(item)

    assert response.extraction_confidence is None
    assert response.validation_status == "UNVERIFIED"


def test_validation_feed_does_not_report_zero_for_unsupported_arithmetic_check():
    metric = SimpleNamespace(
        id=9,
        document_id=13,
        page_number=2,
        mine_name="The all India Prod",
        subsidiary="CIL HQ",
        metric_name="Coal Production",
        fiscal_year="2023-24",
        standard_value=781.05,
        numeric_value=781.05,
        raw_unit="MT",
        standard_unit="MT",
        validation_status="VALIDATED",
        confidence_score=None,
        data_origin="OFFICIAL",
    )

    item = run_deterministic_validation_feed(_Db([(metric, "source.pdf")]))[0]

    assert item["percentage_difference"] is None
    assert item["discrepancy_available"] is False
    assert item["calculated_value"] is None
    assert item["validation_status"] == "UNVERIFIED"
    assert "unavailable" in item["message"].lower()
    ValidationItemResponse.model_validate(item)


def test_validation_feed_reports_zero_only_when_operands_were_actually_compared():
    metric = SimpleNamespace(
        id=10,
        document_id=14,
        page_number=3,
        mine_name="1",
        subsidiary="ECL",
        metric_name="Coal Production",
        fiscal_year="2023-24",
        standard_value=78.105,
        numeric_value=781.05,
        raw_unit="Lakh Tonnes",
        standard_unit="MT",
        validation_status="VALIDATED",
        confidence_score=0.91,
        data_origin="OFFICIAL",
    )

    item = run_deterministic_validation_feed(_Db([(metric, "source.pdf")]))[0]

    assert item["percentage_difference"] == 0.0
    assert item["discrepancy_available"] is True
    assert item["calculated_value"] == 78.105
    assert item["validation_status"] == "VALIDATED"


def test_validation_feed_reports_executed_failed_check_as_warning():
    metric = SimpleNamespace(
        id=11,
        document_id=15,
        page_number=8,
        mine_name="Mine A",
        subsidiary="ECL",
        metric_name="Coal Production",
        fiscal_year="2023-24",
        standard_value=100.0,
        numeric_value=500.0,
        raw_unit="Lakh Tonnes",
        standard_unit="MT",
        validation_status="VALIDATED",
        confidence_score=0.98,
        data_origin="OFFICIAL",
    )

    item = run_deterministic_validation_feed(_Db([(metric, "source.pdf")]))[0]

    assert item["percentage_difference"] == 50.0
    assert item["discrepancy_available"] is True
    assert item["validation_status"] == "WARNING_ARITHMETIC"
    assert item["extraction_confidence"] == 0.98


def test_validation_feed_keeps_unsupported_check_unverified_even_if_metric_says_validated():
    metric = SimpleNamespace(
        id=12,
        document_id=16,
        page_number=9,
        mine_name="The all India Prod",
        subsidiary="CIL HQ",
        metric_name="Coal Production",
        fiscal_year="2023-24",
        standard_value=24.0,
        numeric_value=24.0,
        raw_unit="MT",
        standard_unit="MT",
        validation_status="VALIDATED",
        confidence_score=1.0,
        data_origin="OFFICIAL",
    )

    item = run_deterministic_validation_feed(_Db([(metric, "source.pdf")]))[0]

    assert item["validation_status"] == "UNVERIFIED"
    assert item["percentage_difference"] is None
    assert item["extraction_confidence"] == 1.0
