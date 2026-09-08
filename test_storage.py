import os
import uuid
from app.models import Fact, Provenance, RelationshipType
from app.storage import StorageEngine

TEST_DB = "test_knowledge_layer.db"

def test_storage():
    print("=" * 50)
    print("FAK-LAYER: ASSIGNMENT #2 STORAGE & CONTRACTS TEST")
    print("=" * 50)

    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    storage = StorageEngine(db_path=TEST_DB)
    print("✓ Initialized SQLite schema")

    # 1. Test Document Registration
    inserted = storage.register_document(
        filename="01-delhivery-prospectus-2022-excerpt.pdf",
        file_hash="fakehash123",
        total_pages=100
    )
    assert inserted is True, "Document registration failed"
    print("✓ Document registration validated")

    # 2. Test Fact Ingestion with Provenance
    fact_1 = Fact(
        fact_id="fact_delhivery_inc_01",
        entity="Delhivery Limited",
        canonical_metric="incorporation_date",
        raw_metric="Date of Incorporation",
        value="June 22, 2011",
        provenance=Provenance(
            document_name="01-delhivery-prospectus-2022-excerpt.pdf",
            page_number=1,
            evidence_quote="Our Company was incorporated as 'SSN Logistics Private Limited' on June 22, 2011..."
        )
    )

    fact_2 = Fact(
        fact_id="fact_delhivery_inc_02",
        entity="Delhivery Limited",
        canonical_metric="incorporation_date",
        raw_metric="Incorporated On",
        value="June 22, 2011",
        provenance=Provenance(
            document_name="02-delhivery-annual-report-fy24-excerpt.pdf",
            page_number=2,
            evidence_quote="Delhivery was incorporated on June 22, 2011 under the Companies Act, 1956..."
        )
    )

    storage.insert_facts([
        {**fact_1.model_dump(), **fact_1.provenance.model_dump()},
        {**fact_2.model_dump(), **fact_2.provenance.model_dump()}
    ])
    facts = storage.get_all_facts()
    assert len(facts) == 2, f"Expected 2 facts, got {len(facts)}"
    print("✓ Fact ingestion and relational persistence validated")

    # 3. Test Cross-Document Reconciliation Insertion
    storage.insert_reconciliation({
        "id": str(uuid.uuid4()),
        "fact_a_id": fact_1.fact_id,
        "fact_b_id": fact_2.fact_id,
        "relation_type": RelationshipType.CORROBORATED.value,
        "explanation": "Both documents confirm exact incorporation date of June 22, 2011.",
        "confidence": 1.0
    })

    recs = storage.get_reconciliations()
    assert len(recs) == 1, "Failed to retrieve reconciliations"
    assert recs[0]["relation_type"] == "CORROBORATED"
    print("✓ Cross-document reconciliation link validated")

    # 4. Test Summary Metrics
    stats = storage.get_stats()
    assert stats["total_facts"] == 2
    assert stats["corroborated"] == 1
    print(f"✓ Summary statistics verified: {stats}")

    # Cleanup test DB
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    print("\n" + "=" * 50)
    print("STATUS: Assignment #2 passed with 0 errors!")
    print("=" * 50)

if __name__ == "__main__":
    test_storage()