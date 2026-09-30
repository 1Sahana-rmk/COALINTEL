"""Focused regression coverage for the minimal four-role RBAC hardening pass."""

import os
import sys

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from main import app
from app.core.rbac import (
    ADMIN_ONLY_ROLES,
    INGESTION_ROLES,
    REPORT_GENERATION_ROLES,
    REVIEW_ROLES,
    RoleChecker,
)
from app.models.user import User
from app.api import audit, documents, mines, query, reports, sources, validation


ROLES = ("Admin", "Reviewer", "Analyst", "Viewer")


ROLE_MATRIX = {
    "document_upload": INGESTION_ROLES,
    "document_delete": ADMIN_ONLY_ROLES,
    "official_source_sync": ADMIN_ONLY_ROLES,
    "conflict_recompute": ADMIN_ONLY_ROLES,
    "conflict_resolve": REVIEW_ROLES,
    "report_generate": REPORT_GENERATION_ROLES,
    "report_approve": REVIEW_ROLES,
    "audit_read": ADMIN_ONLY_ROLES,
    "vector_index": INGESTION_ROLES,
}


def _route(router, path, method):
    for route in router.routes:
        if route.path == path and method.upper() in route.methods:
            return route
    raise AssertionError(f"Route {method} {path} not found")


def _role_checker_for_route(route):
    for dependency in route.dependant.dependencies:
        if isinstance(dependency.call, RoleChecker):
            return dependency.call
    raise AssertionError(f"No RoleChecker dependency found for {route.path}")


def test_protected_endpoint_wiring_matches_role_matrix():
    route_specs = {
        "document_upload": (_route(documents.router, "/documents/upload", "POST")),
        "document_delete": (_route(documents.router, "/documents/{id}", "DELETE")),
        "official_source_sync": (_route(sources.router, "/sources/ministry-of-coal/sync", "POST")),
        "conflict_recompute": (_route(validation.router, "/conflicts/recompute", "POST")),
        "conflict_resolve": (_route(validation.router, "/conflicts/{id}/resolve", "POST")),
        "report_generate": (_route(reports.router, "/reports/generate", "POST")),
        "report_approve": (_route(reports.router, "/reports/{id}/approve", "POST")),
        "audit_read": (_route(audit.router, "/audit/logs", "GET")),
        "vector_index": (_route(query.router, "/query/index-document/{id}", "POST")),
    }

    for name, route in route_specs.items():
        checker = _role_checker_for_route(route)
        assert checker.allowed_roles == ROLE_MATRIX[name]


@pytest.mark.parametrize("action,allowed_roles", ROLE_MATRIX.items())
def test_all_four_roles_are_evaluated_against_each_privileged_action(action, allowed_roles):
    """Verify the explicit Admin/Reviewer/Analyst/Viewer action matrix."""
    checker = RoleChecker(allowed_roles)
    for role in ROLES:
        user = User(id=role.__hash__() & 0x7FFFFFFF, username=role.lower(), role=role)
        if role in allowed_roles:
            assert checker(user) is user, f"{role} should be allowed for {action}"
        else:
            with pytest.raises(HTTPException) as exc_info:
                checker(user)
            assert exc_info.value.status_code == 403, f"{role} should be denied for {action}"


def test_mines_and_legacy_data_endpoints_require_authentication():
    client = TestClient(app)
    protected_paths = [
        "/api/v1/mines",
        "/api/v1/mines/stats",
        "/api/v1/mines-summary-stats",
        "/api/v1/coal-blocks",
        "/api/v1/mines/coal-blocks",
        "/api/v1/data-sources",
        "/api/v1/mines/data-sources",
        "/api/v1/data-conflicts",
        "/api/v1/mines/conflicts",
        "/api/v1/data-validations",
        "/api/v1/mines/validations",
        "/api/v1/mines/MINE-SECL-GEVRA",
    ]

    for path in protected_paths:
        response = client.get(path)
        assert response.status_code == 401, f"Unauthenticated {path} was not rejected"


def test_mines_router_has_authentication_dependency_without_schema_change():
    dependency_calls = [dependency.dependency for dependency in mines.router.dependencies]
    assert any(call.__name__ == "get_current_user" for call in dependency_calls)
