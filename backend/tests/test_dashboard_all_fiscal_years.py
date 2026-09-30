import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database import Base
from app.api.dashboard import get_dashboard_charts, get_dashboard_kpis
from app.models.document import Document
from app.models.extracted_metric import ExtractedMetric


def _session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _seed_two_years(db):
    docs = [
        Document(
            filename="fy22.pdf",
            file_path="fy22.pdf",
            file_hash="fy22-hash",
            file_type="PDF",
            subsidiary="SECL",
            fiscal_year="2022-23",
            status="PARSED",
        ),
        Document(
            filename="fy23.pdf",
            file_path="fy23.pdf",
            file_hash="fy23-hash",
            file_type="PDF",
            subsidiary="SECL",
            fiscal_year="2023-24",
            status="PARSED",
        ),
    ]
    db.add_all(docs)
    db.flush()
    db.add_all([
        ExtractedMetric(
            document_id=docs[0].id,
            page_number=1,
            mine_name="Gevra OC",
            subsidiary="SECL",
            metric_name="Coal Production",
            numeric_value=10,
            unit="MT",
            standard_value=10,
            standard_unit="MT",
            fiscal_year="2022-23",
            confidence_score=0.9,
            validation_status="VALIDATED",
        ),
        ExtractedMetric(
            document_id=docs[1].id,
            page_number=1,
            mine_name="Gevra OC",
            subsidiary="SECL",
            metric_name="Coal Production",
            numeric_value=20,
            unit="MT",
            standard_value=20,
            standard_unit="MT",
            fiscal_year="2023-24",
            confidence_score=0.9,
            validation_status="VALIDATED",
        ),
    ])
    db.commit()


def test_all_years_does_not_sum_annual_production():
    db = _session()
    try:
        _seed_two_years(db)
        all_years = get_dashboard_kpis("ALL", "SECL", db, None)
        assert all_years.total_production_mt == "20.00"
        assert all_years.total_production_period == "FY 2023-24"
        assert all_years.total_obr_mcum == "N/A"
        assert all_years.total_obr_period is None

        fy_22 = get_dashboard_kpis("2022-23", "SECL", db, None)
        assert fy_22.total_production_mt == "10.00"
    finally:
        db.close()


def test_all_years_uses_scope_specific_latest_observation_and_labels_ytd():
    db = _session()
    try:
        _seed_two_years(db)
        ytd_doc = Document(
            filename="fy24-ytd.pdf",
            file_path="fy24-ytd.pdf",
            file_hash="fy24-ytd-hash",
            file_type="PDF",
            subsidiary="SECL",
            fiscal_year="2024-25",
            reporting_period="Q1 YTD Provisional",
            status="PARSED",
        )
        ecl_doc = Document(
            filename="ecl-fy24.pdf",
            file_path="ecl-fy24.pdf",
            file_hash="ecl-fy24-hash",
            file_type="PDF",
            subsidiary="ECL",
            fiscal_year="2024-25",
            status="PARSED",
        )
        db.add_all([ytd_doc, ecl_doc])
        db.flush()
        db.add_all([
            ExtractedMetric(
                document_id=ytd_doc.id,
                page_number=1,
                mine_name="Gevra OC",
                subsidiary="SECL",
                metric_name="Coal Production",
                numeric_value=30,
                unit="MT",
                standard_value=30,
                standard_unit="MT",
                fiscal_year="2024-25",
                validation_status="VALIDATED",
            ),
            ExtractedMetric(
                document_id=ecl_doc.id,
                page_number=1,
                mine_name="Rajmahal OC",
                subsidiary="ECL",
                metric_name="Coal Production",
                numeric_value=40,
                unit="MT",
                standard_value=40,
                standard_unit="MT",
                fiscal_year="2024-25",
                validation_status="VALIDATED",
            ),
        ])
        db.commit()

        secl = get_dashboard_kpis("ALL", "SECL", db, None)
        assert secl.total_production_mt == "30.00"
        assert secl.total_production_period == "FY 2024-25 (YTD Provisional)"

        ecl = get_dashboard_kpis("ALL", "ECL", db, None)
        assert ecl.total_production_mt == "40.00"
        assert ecl.total_production_period == "FY 2024-25"

        missing = get_dashboard_kpis("ALL", "MCL", db, None)
        assert missing.total_production_mt == "N/A"
        assert missing.total_production_period is None
    finally:
        db.close()


def test_all_years_chart_preserves_fiscal_year_dimension():
    db = _session()
    try:
        _seed_two_years(db)
        chart = get_dashboard_charts("ALL", "SECL", db, None)
        assert chart.available_fiscal_years == ["2023-24", "2022-23"]
        assert [(item.fiscal_year, item.actual) for item in chart.production_data] == [
            ("2022-23", 10.0),
            ("2023-24", 20.0),
        ]
    finally:
        db.close()
