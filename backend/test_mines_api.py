from fastapi.testclient import TestClient
from main import app


def test_enhanced_government_mines_api():
    client = TestClient(app)

    print("--- TESTING ENHANCED GOVERNMENT MINES API (PHASE 6) ---")

    # 1. /api/v1/mines
    r_mines = client.get("/api/v1/mines")
    print("GET /api/v1/mines status:", r_mines.status_code)
    assert r_mines.status_code == 200
    mines = r_mines.json()
    print(f"Total canonical mines returned: {len(mines)}")
    assert len(mines) >= 60, f"Expected at least 60 mines, got {len(mines)}"
    assert "X-Total-Count" in r_mines.headers
    total_count = int(r_mines.headers["X-Total-Count"])
    print(f"X-Total-Count header: {total_count}")
    assert total_count >= 60

    # 2. /api/v1/mines/stats
    r_stats = client.get("/api/v1/mines/stats")
    print("\nGET /api/v1/mines/stats status:", r_stats.status_code)
    assert r_stats.status_code == 200
    stats = r_stats.json()
    print(f"Stats total mines: {stats['total_canonical_mines']}")
    print(f"Coverage states: {stats['coverage']['states_covered']}")
    print(f"Breakdowns by fuel: {stats['breakdowns']['by_fuel']}")
    print(f"Breakdowns by mine type: {stats['breakdowns']['by_type']}")
    print(f"Breakdowns by operational status: {stats['breakdowns']['by_status']}")
    assert stats['total_canonical_mines'] >= 60
    assert stats['coverage']['coal_mines_count'] >= 50
    assert stats['coverage']['lignite_mines_count'] >= 10

    # 3. /api/v1/mines/states
    r_states = client.get("/api/v1/mines/states")
    print("\nGET /api/v1/mines/states status:", r_states.status_code)
    assert r_states.status_code == 200
    states = r_states.json()
    print(f"States count: {len(states)}, Sample: {[s['name'] for s in states[:4]]}")
    assert len(states) >= 12
    assert any(s["name"] == "Tamil Nadu" for s in states)
    assert any(s["name"] == "Gujarat" for s in states)
    assert any(s["name"] == "Rajasthan" for s in states)
    assert any(s["name"] == "Assam" for s in states)

    # 4. /api/v1/mines/subsidiaries
    r_subs = client.get("/api/v1/mines/subsidiaries")
    print("\nGET /api/v1/mines/subsidiaries status:", r_subs.status_code)
    assert r_subs.status_code == 200
    subs = r_subs.json()
    print(f"Subsidiaries count: {len(subs)}, Sample: {[s['name'] for s in subs[:4]]}")
    assert any(s["name"] == "NLCIL" for s in subs)
    assert any(s["name"] == "GMDC" for s in subs)

    # 5. /api/v1/mines/sectors
    r_sec = client.get("/api/v1/mines/sectors")
    print("\nGET /api/v1/mines/sectors status:", r_sec.status_code)
    assert r_sec.status_code == 200
    sectors = r_sec.json()
    print(f"Sectors count: {len(sectors)}, List: {[s['name'] for s in sectors]}")
    assert any(s["name"] == "Commercial" for s in sectors)
    assert any(s["name"] == "Private" for s in sectors)

    # 6. /api/v1/mines/types
    r_types = client.get("/api/v1/mines/types")
    print("\nGET /api/v1/mines/types status:", r_types.status_code)
    assert r_types.status_code == 200
    mtypes = r_types.json()
    print(f"Mine types: {mtypes}")
    assert any(t["name"] == "Mixed" for t in mtypes)
    assert any(t["name"] == "OC" for t in mtypes)
    assert any(t["name"] == "UG" for t in mtypes)

    # 7. /api/v1/mines/companies
    r_comp = client.get("/api/v1/mines/companies")
    print("\nGET /api/v1/mines/companies status:", r_comp.status_code)
    assert r_comp.status_code == 200
    comp = r_comp.json()
    print(f"Companies count: {len(comp)}")
    assert any("Tata Steel" in c["name"] for c in comp)
    assert any("NLC India" in c["name"] for c in comp)

    # 8. Filtered queries
    # Lignite filter
    r_lig = client.get("/api/v1/mines?coal_or_lignite=Lignite")
    assert r_lig.status_code == 200
    assert len(r_lig.json()) >= 10

    # Mixed type filter
    r_mixed = client.get("/api/v1/mines?mine_type=Mixed")
    assert r_mixed.status_code == 200
    assert len(r_mixed.json()) >= 4

    # Operational status filter
    r_dev = client.get("/api/v1/mines?status=UNDER_DEVELOPMENT")
    assert r_dev.status_code == 200
    assert len(r_dev.json()) >= 3

    # Sorting by production desc
    r_sort = client.get("/api/v1/mines?sort_by=production&sort_order=desc")
    assert r_sort.status_code == 200
    top_mine = r_sort.json()[0]
    print(f"\nTop producing mine: {top_mine['mine_name']} with {top_mine['production_fy25_26']} MT")
    assert top_mine["production_fy25_26"] is not None and top_mine["production_fy25_26"] > 50

    # 9. Single mine detail
    sample_id = top_mine["mine_id"]
    r_det = client.get(f"/api/v1/mines/{sample_id}")
    assert r_det.status_code == 200
    det = r_det.json()
    print(f"Mine detail for {det['mine_name']}: {len(det['yearly_metrics'])} yearly metrics")
    assert len(det["yearly_metrics"]) == 3

    # 10. Backward-compatible alias /mines-summary-stats
    r_alias = client.get("/api/v1/mines-summary-stats")
    assert r_alias.status_code == 200

    print("\n--- ALL PHASE 6 BACKEND API TESTS PASSED SUCCESSFULLY! ---")


if __name__ == "__main__":
    test_enhanced_government_mines_api()
