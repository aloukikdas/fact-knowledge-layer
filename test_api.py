import os
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_fastapi_endpoints():
    print("=" * 50)
    print("FAK-LAYER: ASSIGNMENT #6 FASTAPI ENDPOINTS TEST")
    print("=" * 50)

    # 1. Test Seed Endpoint
    print("\n[1/4] Testing /api/seed-verified-cases...")
    seed_res = client.post("/api/seed-verified-cases")
    assert seed_res.status_code == 200, f"Seed failed: {seed_res.text}"
    print("✓ Successfully triggered verified cases seeder")

    # 2. Test Stats Endpoint
    print("\n[2/4] Testing /api/stats...")
    stats_res = client.get("/api/stats")
    assert stats_res.status_code == 200, f"Stats failed: {stats_res.text}"
    stats = stats_res.json()
    print(f"  • Retrieved Stats: {stats}")
    assert stats["total_documents"] >= 3, "Expected documents count to be >= 3"
    assert stats["total_facts"] >= 8, "Expected facts count to be >= 8"
    assert stats["corroborated"] >= 1, "Corroborations missing in stats"
    assert stats["reconciled"] >= 1, "Reconciled missing in stats"
    assert stats["contradiction"] >= 1, "Contradictions missing in stats"
    assert stats["edge_case"] >= 1, "Edge cases missing in stats"
    print("✓ /api/stats validated")

    # 3. Test Facts Endpoint
    print("\n[3/4] Testing /api/facts...")
    facts_res = client.get("/api/facts")
    assert facts_res.status_code == 200
    facts = facts_res.json()
    print(f"  • Retrieved {len(facts)} facts from knowledge layer")
    assert len(facts) >= 8
    print("✓ /api/facts validated")

    # 4. Test Reconciliations Endpoint with filters for all 4 cases
    print("\n[4/4] Testing /api/reconciliations filters...")
    for rel_type in ["CORROBORATED", "RECONCILED", "CONTRADICTION", "EDGE_CASE"]:
        r_res = client.get(f"/api/reconciliations?type={rel_type}")
        assert r_res.status_code == 200
        items = r_res.json()
        print(f"  • {rel_type}: {len(items)} record(s) retrieved")
        assert len(items) >= 1, f"No records found for {rel_type}"

    print("\n" + "=" * 50)
    print("STATUS: Assignment #6 passed with 0 errors!")
    print("=" * 50)

if __name__ == "__main__":
    test_fastapi_endpoints()