import os
from app.models import Fact, Provenance, RelationshipType
from app.reconciler import ReconciliationEngine
from app.storage import StorageEngine

TEST_DB = "test_reconciliation.db"

def test_four_cases():
    print("=" * 50)
    print("FAK-LAYER: ASSIGNMENT #5 4-CASE RECONCILIATION TEST")
    print("=" * 50)

    engine = ReconciliationEngine()
    storage = StorageEngine(db_path=TEST_DB)

    # -------------------------------------------------------------
    # CASE 1: CORROBORATION
    # -------------------------------------------------------------
    print("\n[Case 1/4] Testing Corroboration across filings...")
    fact_c1_a = Fact(
        fact_id="c1_prospectus_cin",
        entity="Delhivery Limited",
        canonical_metric="corporate_identity_number",
        raw_metric="CIN",
        value="U63090DL2011PLC221234",
        period="Permanent",
        provenance=Provenance(
            document_name="01-delhivery-prospectus-2022-excerpt.pdf",
            page_number=1,
            evidence_quote="CORPORATE IDENTITY NUMBER: U63090DL2011PLC221234"
        )
    )
    fact_c1_b = Fact(
        fact_id="c1_annual_cin",
        entity="Delhivery Limited",
        canonical_metric="corporate_identity_number",
        raw_metric="Corporate Identity Number (CIN)",
        value="U63090DL2011PLC221234",
        period="Permanent",
        provenance=Provenance(
            document_name="02-delhivery-annual-report-fy24-excerpt.pdf",
            page_number=2,
            evidence_quote="CIN: U63090DL2011PLC221234"
        )
    )

    rel_1 = engine.arbitrate_pair(fact_c1_a, fact_c1_b)
    print(f"  • Classification: {rel_1.relation.value}")
    print(f"  • Explanation: {rel_1.explanation}")
    assert rel_1.relation == RelationshipType.CORROBORATED, f"Expected CORROBORATED, got {rel_1.relation}"
    print("✓ Case 1 (Corroboration) verified successfully!")

    # -------------------------------------------------------------
    # CASE 2: APPARENT CONTRADICTION RECONCILED BY CONTEXT
    # -------------------------------------------------------------
    print("\n[Case 2/4] Testing Apparent Contradiction Reconciled by Context (Time/Scope)...")
    fact_c2_a = Fact(
        fact_id="c2_revenue_9m",
        entity="Delhivery Limited",
        canonical_metric="revenue_from_operations",
        raw_metric="Revenue from operations",
        value=48112.82,
        unit="INR Million",
        period="9M ended December 31, 2021",
        scope="Restated Consolidated",
        context_notes="Nine-month stub period financials included in IPO DRHP prospectus",
        provenance=Provenance(
            document_name="01-delhivery-prospectus-2022-excerpt.pdf",
            page_number=26,
            evidence_quote="Revenue from operations for the nine months ended December 31, 2021 was ₹48,112.82 million"
        )
    )
    fact_c2_b = Fact(
        fact_id="c2_revenue_fy22",
        entity="Delhivery Limited",
        canonical_metric="revenue_from_operations",
        raw_metric="Revenue from Operations",
        value=68822.93,
        unit="INR Million",
        period="Full Year FY 2021-22 (12 Months ended March 31, 2022)",
        scope="Audited Consolidated",
        context_notes="Full 12-month fiscal audited year reported historically in subsequent filing",
        provenance=Provenance(
            document_name="02-delhivery-annual-report-fy24-excerpt.pdf",
            page_number=110,
            evidence_quote="Revenue from Operations for FY22 stood at ₹68,822.93 million"
        )
    )

    rel_2 = engine.arbitrate_pair(fact_c2_a, fact_c2_b)
    print(f"  • Classification: {rel_2.relation.value}")
    print(f"  • Explanation: {rel_2.explanation}")
    assert rel_2.relation == RelationshipType.RECONCILED, f"Expected RECONCILED, got {rel_2.relation}"
    print("✓ Case 2 (Apparent Contradiction Reconciled) verified successfully!")

    # -------------------------------------------------------------
    # CASE 3: GENUINE CONTRADICTION
    # -------------------------------------------------------------
    print("\n[Case 3/4] Testing Genuine Contradiction (Same period/metric, clashing value)...")
    fact_c3_a = Fact(
        fact_id="c3_pincodes_doc_a",
        entity="Delhivery Limited",
        canonical_metric="pin_codes_covered",
        raw_metric="Pin codes covered",
        value=17500,
        unit="Count",
        period="As of June 30, 2021",
        scope="Consolidated",
        context_notes="Nationwide network reach",
        provenance=Provenance(
            document_name="01-delhivery-prospectus-2022-excerpt.pdf",
            page_number=10,
            evidence_quote="As of June 30, 2021, our network covered 17,500 pin codes across India."
        )
    )
    fact_c3_b = Fact(
        fact_id="c3_pincodes_doc_b",
        entity="Delhivery Limited",
        canonical_metric="pin_codes_covered",
        raw_metric="PIN codes serviced",
        value=19200,
        unit="Count",
        period="As of June 30, 2021",
        scope="Consolidated",
        context_notes="Nationwide network reach without any qualifier",
        provenance=Provenance(
            document_name="03-delhivery-q4-fy24-earnings-presentation.pdf",
            page_number=5,
            evidence_quote="Historical footprint: Covered 19,200 pin codes as of June 30, 2021."
        )
    )

    rel_3 = engine.arbitrate_pair(fact_c3_a, fact_c3_b)
    print(f"  • Classification: {rel_3.relation.value}")
    print(f"  • Explanation: {rel_3.explanation}")
    assert rel_3.relation == RelationshipType.CONTRADICTION, f"Expected CONTRADICTION, got {rel_3.relation}"
    print("✓ Case 3 (Genuine Contradiction) verified successfully!")

    # -------------------------------------------------------------
    # CASE 4: EXTRACTION & REASONING FAILURE / EDGE CASE
    # -------------------------------------------------------------
    print("\n[Case 4/4] Testing Extraction/Reasoning Edge Case...")
    fact_c4_a = Fact(
        fact_id="c4_ebitda_raw",
        entity="Delhivery Limited",
        canonical_metric="adjusted_ebitda",
        raw_metric="Adjusted EBITDA",
        value=1200.5,
        unit="INR Million",
        period="FY 2023-24",
        context_notes="Extracted from top of table; footnote (2) was detached on next page chunk",
        provenance=Provenance(
            document_name="02-delhivery-annual-report-fy24-excerpt.pdf",
            page_number=45,
            evidence_quote="Adjusted EBITDA: ₹1,200.5 million*(2)"
        )
    )
    fact_c4_b = Fact(
        fact_id="c4_ebitda_with_footnote",
        entity="Delhivery Limited",
        canonical_metric="adjusted_ebitda",
        raw_metric="Adjusted EBITDA (Excluding ESOPs)",
        value=720.0,
        unit="INR Million",
        period="FY 2023-24",
        context_notes="Footnote (2) explicitly subtracts non-cash share based payment expense of ₹480.5M",
        provenance=Provenance(
            document_name="03-delhivery-q4-fy24-earnings-presentation.pdf",
            page_number=12,
            evidence_quote="Adjusted EBITDA post-ESOP charge: ₹720.0 million"
        )
    )

    rel_4 = engine.arbitrate_pair(fact_c4_a, fact_c4_b)
    print(f"  • Classification: {rel_4.relation.value}")
    print(f"  • Explanation: {rel_4.explanation}")
    assert rel_4.relation in [RelationshipType.EDGE_CASE, RelationshipType.RECONCILED], "Edge case classification failed"
    print("✓ Case 4 (Edge Case / Footnote Discrepancy) verified successfully!")

    # -------------------------------------------------------------
    # PERSISTENCE CHECK
    # -------------------------------------------------------------
    print("\n[Storage Check] Writing facts and relations to SQLite knowledge layer...")
    all_test_facts = [fact_c1_a, fact_c1_b, fact_c2_a, fact_c2_b, fact_c3_a, fact_c3_b, fact_c4_a, fact_c4_b]
    storage.insert_facts([{**f.model_dump(), **f.provenance.model_dump()} for f in all_test_facts])

    for rel in [rel_1, rel_2, rel_3, rel_4]:
        storage.insert_reconciliation({
            "id": rel.relation_id,
            "fact_a_id": rel.fact_a.fact_id,
            "fact_b_id": rel.fact_b.fact_id,
            "relation_type": rel.relation.value,
            "explanation": rel.explanation,
            "confidence": rel.confidence
        })

    stats = storage.get_stats()
    print(f"✓ Stored Knowledge Layer Stats: {stats}")
    assert stats["total_facts"] == 8
    assert stats["corroborated"] >= 1
    assert stats["reconciled"] >= 1
    assert stats["contradiction"] >= 1

    # Cleanup test DB
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

    print("\n" + "=" * 50)
    print("STATUS: Assignment #5 passed with 0 errors!")
    print("=" * 50)

if __name__ == "__main__":
    test_four_cases()