from types import SimpleNamespace

from app.services.assistant_service import (
    _citation_from_reference,
    _conflict_states,
    _structured_claims,
    _source_reference,
)
from app.services.rag_service import extract_and_validate_citations


def _fact(value, fact_id, document_id, page, table_id, locator=None):
    return {
        "fact_id": fact_id,
        "document_id": document_id,
        "page_number": page,
        "table_id": table_id,
        "entity": {"canonical": "ECL", "raw": "ECL"},
        "metric": {"canonical": "Coal Production", "raw": "Coal Production"},
        "value": {"raw": str(value), "normalized": value, "raw_unit": "MT", "normalized_unit": "MT"},
        "period": {"raw": "FY 2023-24", "normalized": "FY 2023-24"},
        "evidence_type": "TABLE_CELL",
        "evidence_locator": locator or {},
        "extraction_method": "NATIVE_TABLE",
        "extraction_confidence": 0.98,
        "validation_status": "CHECK_EXECUTED_PASSED",
        "fact_status": "ACCEPTED",
        "filename": f"report-{document_id}.pdf",
        "source_url": "https://coal.gov.in/reports/report.pdf",
        "source_type": "OFFICIAL",
    }


def test_structured_claims_and_citations_are_narrow_and_distinct():
    facts = [
        _fact(16, 1, 10, 8, 4, {"row_index": 2, "column_index": 5, "cell_text": "16"}),
        _fact(17, 2, 11, 9, 7, {"row_index": 3, "column_index": 6, "cell_text": "17"}),
    ]
    claims = _structured_claims(facts)
    assert len(claims) == 2
    assert claims[0]["evidence"][0]["table_id"] == 4
    assert claims[1]["evidence"][0]["document_id"] == 11

    citation = _citation_from_reference(_source_reference(facts[0]))
    assert citation["document_id"] == 10
    assert citation["table_id"] == 4
    assert citation["locator"]["column_index"] == 5
    assert citation["source_url"].startswith("https://")


def test_missing_locator_is_preserved_as_missing_not_fabricated():
    ref = _source_reference({"document_id": 10, "filename": "report.pdf", "page_number": 2})
    citation = _citation_from_reference(ref)
    assert citation["locator"] == {}
    assert citation["table_id"] is None


def test_hallucinated_or_out_of_packet_citations_are_rejected():
    evidence = [{"filename": "report.pdf", "page_number": 8, "text": "ECL coal production 16 MT"}]
    citations, passed = extract_and_validate_citations(
        "The answer is 16 MT [other.pdf, Page 99] [report.pdf, Page 8]",
        evidence,
        query_text="What was ECL coal production?",
    )
    assert passed is True
    assert [item["document_name"] for item in citations] == ["report.pdf"]


def test_conflict_status_is_preserved_and_not_resolved_by_averaging():
    group = [_fact(16, 1, 10, 8, 4), _fact(18, 2, 11, 9, 7)]

    class FakeQuery:
        def filter(self, *args, **kwargs):
            return self

        def all(self):
            return [SimpleNamespace(id=55, doc_a_id=10, doc_b_id=11, status="RESOLVED")]

    class FakeDb:
        def query(self, _model):
            return FakeQuery()

    states = _conflict_states(FakeDb(), [group])
    assert states == [{"status": "RESOLVED", "conflict_ids": [55], "candidate_count": 2}]
    assert {fact["value"]["normalized"] for fact in group} == {16, 18}
