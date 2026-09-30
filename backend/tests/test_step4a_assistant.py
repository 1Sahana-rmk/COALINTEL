from unittest.mock import patch

from app.services.assistant_service import analyze_query, execute_assistant_query
from app.api.query import router as query_router


def _fact(value, *, document_id=10, page=4, entity="ECL", metric="Coal Production", period="FY 2023-24"):
    return {
        "fact_id": int(value * 10),
        "document_id": document_id,
        "page_id": 100,
        "page_number": page,
        "table_id": 20,
        "entity": {"type": "SUBSIDIARY", "raw": entity, "canonical": entity},
        "metric": {"type": "COAL_PRODUCTION", "raw": metric, "canonical": metric},
        "value": {"raw": str(value), "raw_numeric": value, "normalized": value, "raw_unit": "MT", "normalized_unit": "MT"},
        "period": {"raw": period, "normalized": period, "type": "FISCAL_YEAR"},
        "evidence_type": "TABLE_CELL",
        "evidence_locator": {"table_id": 20, "row_index": 2, "column_index": 3},
        "validation_status": "CHECK_EXECUTED_PASSED",
        "fact_status": "ACCEPTED",
        "extraction_method": "NATIVE_TABLE",
        "extraction_confidence": 0.98,
    }


def _semantic_item(document_id=10):
    return [{
        "chunk_id": 8,
        "document_id": document_id,
        "page_id": 100,
        "page_number": 4,
        "chunk_index": 2,
        "chunk_type": "TEXT_BLOCK",
        "text": "ECL coal production increased during FY 2023-24.",
        "retrieval_score": 0.91,
        "source_locator": {"page_number": 4},
    }]


def test_query_analysis_routes_representative_questions():
    structured = analyze_query("What was ECL coal production in November 2020?")
    assert structured["route"] == "STRUCTURED"
    assert structured["filters"]["subsidiary"] == "ECL"
    assert structured["filters"]["period"] == "November 2020"

    semantic = analyze_query("What is the policy for coal dispatch reporting?")
    assert semantic["route"] == "SEMANTIC"

    hybrid = analyze_query("Compare ECL production with the contextual explanation in the reports.")
    assert hybrid["route"] == "HYBRID"


def test_structured_query_uses_facts_and_preserves_conflicts():
    facts = [_fact(16.0), _fact(18.0, document_id=11, page=7)]
    with patch("app.services.assistant_service._has_step3_tables", return_value=True), \
         patch("app.services.assistant_service.search_structured_facts", return_value={"status": "OK", "count": 2, "results": facts}), \
         patch("app.services.assistant_service._structured_items_with_filenames", return_value=[{**fact, "filename": "ecl.pdf"} for fact in facts]), \
         patch("app.services.assistant_service.semantic_search") as semantic:
        result = execute_assistant_query(object(), "What was ECL coal production in FY 2023-24?", top_k=5)

    semantic.assert_not_called()
    assert result["route"] == "STRUCTURED"
    assert result["support_state"] == "CONFLICTING"
    assert len(result["structured_facts"]) == 2
    assert result["source_references"][0]["table_id"] == 20
    assert "16.0" in result["answer"]
    assert "18.0" in result["answer"]


def test_semantic_query_uses_pgvector_and_not_structured_facts():
    semantic = _semantic_item()
    with patch("app.services.assistant_service._has_step3_tables", return_value=True), \
         patch("app.services.assistant_service.search_structured_facts") as structured, \
         patch("app.services.assistant_service.semantic_search", return_value={"status": "OK", "count": 1, "results": semantic}), \
         patch("app.services.assistant_service._semantic_items_with_filenames", return_value=[{**semantic[0], "filename": "report.pdf", "rrf_score": 0.91, "vector_score": 0.91}]), \
         patch("app.services.assistant_service._semantic_answer", return_value=("Grounded explanation [report.pdf, Page 4]", [{"document_name": "report.pdf", "page_number": 4, "citation_tag": "[report.pdf, Page 4]"}], "SUPPORTED", False, [{"claim_id": "answer-1", "evidence": []}])):
        result = execute_assistant_query(object(), "What is the policy for coal dispatch reporting?")

    structured.assert_not_called()
    assert result["route"] == "SEMANTIC"
    assert result["support_state"] == "SUPPORTED"
    assert result["semantic_evidence"][0]["filename"] == "report.pdf"


def test_hybrid_query_invokes_both_and_returns_separate_evidence():
    facts = [_fact(16.0)]
    semantic = _semantic_item()
    with patch("app.services.assistant_service._has_step3_tables", return_value=True), \
         patch("app.services.assistant_service.search_structured_facts", return_value={"status": "OK", "count": 1, "results": facts}) as structured, \
         patch("app.services.assistant_service._structured_items_with_filenames", return_value=[{**facts[0], "filename": "ecl.pdf"}]), \
         patch("app.services.assistant_service.semantic_search", return_value={"status": "OK", "count": 1, "results": semantic}) as semantic_search, \
         patch("app.services.assistant_service._semantic_items_with_filenames", return_value=[{**semantic[0], "filename": "report.pdf", "rrf_score": 0.91, "vector_score": 0.91}]), \
         patch("app.services.assistant_service._semantic_answer", return_value=("Grounded comparison [report.pdf, Page 4]", [{"document_name": "report.pdf", "page_number": 4, "citation_tag": "[report.pdf, Page 4]"}], "SUPPORTED", True, [{"claim_id": "answer-1", "evidence": []}])):
        result = execute_assistant_query(object(), "Compare ECL production with the contextual explanation in the reports.")

    assert result["route"] == "HYBRID"
    structured.assert_called_once()
    semantic_search.assert_called_once()
    assert result["structured_facts"] and result["semantic_evidence"]
    assert result["conflicts"] == []


def test_missing_store_and_embedding_unavailable_are_explicit():
    with patch("app.services.assistant_service._has_step3_tables", return_value=False):
        result = execute_assistant_query(object(), "What was ECL coal production in FY 2023-24?")
    assert result["support_state"] == "UNAVAILABLE"
    assert result["generation_status"] == "KNOWLEDGE_STORE_UNAVAILABLE"

    with patch("app.services.assistant_service._has_step3_tables", return_value=True), \
         patch("app.services.assistant_service.semantic_search", return_value={"status": "UNAVAILABLE", "count": 0, "results": [], "reason": "model unavailable"}):
        result = execute_assistant_query(object(), "What is the policy for coal dispatch reporting?")
    assert result["support_state"] == "UNSUPPORTED"
    assert result["generation_status"] == "UNAVAILABLE"
    assert "unavailable" in result["answer"].lower()


def test_query_route_requires_existing_authenticated_dependency():
    route = next(route for route in query_router.routes if getattr(route, "path", "") == "/query/ask")
    dependency_callables = [dependency.call for dependency in route.dependant.dependencies]
    assert any(getattr(callable_, "__name__", "") == "get_current_user" for callable_ in dependency_callables)
