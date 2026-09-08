from app.models import Fact, Provenance, RelationshipType
from app.storage import StorageEngine


def seed_verified_data(storage: StorageEngine):
    # Register the 3 starter documents
    docs = [
        ("01-delhivery-prospectus-2022-excerpt.pdf", "hash_delhivery_prospectus_2022", 100),
        ("02-delhivery-annual-report-fy24-excerpt.pdf", "hash_delhivery_annual_report_fy24", 100),
        ("03-delhivery-q4-fy24-earnings-presentation.pdf", "hash_delhivery_q4_fy24_presentation", 27),
    ]
    for filename, file_hash, pages in docs:
        storage.register_document(filename, file_hash, pages)

    # Case 1: Corroboration
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

    # Case 2: Apparent Contradiction Reconciled by Context
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

    # Case 3: Genuine Contradiction
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

    # Case 4: Edge Case / Footnote Discrepancy
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
    all_facts = [fact_c1_a, fact_c1_b, fact_c2_a, fact_c2_b, fact_c3_a, fact_c3_b, fact_c4_a, fact_c4_b]
    storage.insert_facts([{**f.model_dump(), **f.provenance.model_dump()} for f in all_facts])
    reconciliations = [
        {
            "id": "rel_c1_cin",
            "fact_a_id": fact_c1_a.fact_id,
            "fact_b_id": fact_c1_b.fact_id,
            "relation_type": RelationshipType.CORROBORATED.value,
            "explanation": "Both filings corroborate the identical corporate identifier (CIN: U63090DL2011PLC221234) for Delhivery Limited.",
            "confidence": 1.0
        },
        {
            "id": "rel_c2_revenue",
            "fact_a_id": fact_c2_a.fact_id,
            "fact_b_id": fact_c2_b.fact_id,
            "relation_type": RelationshipType.RECONCILED.value,
            "explanation": "Apparent contradiction reconciled by context: Fact A represents a 9-month stub period ended Dec 31, 2021 (₹48,112.82M) reported in the IPO DRHP, whereas Fact B represents the full 12-month FY22 fiscal year (₹68,822.93M) audited in subsequent annual filings.",
            "confidence": 0.98
        },
        {
            "id": "rel_c3_pincodes",
            "fact_a_id": fact_c3_a.fact_id,
            "fact_b_id": fact_c3_b.fact_id,
            "relation_type": RelationshipType.CONTRADICTION.value,
            "explanation": "Genuine contradiction identified: Conflicting figures (17,500 vs 19,200 pin codes) reported for the exact same entity and date (As of June 30, 2021) without qualifying scope or explanatory footnotes.",
            "confidence": 0.95
        },
        {
            "id": "rel_c4_ebitda",
            "fact_a_id": fact_c4_a.fact_id,
            "fact_b_id": fact_c4_b.fact_id,
            "relation_type": RelationshipType.EDGE_CASE.value,
            "explanation": "Extraction edge case identified: Fact A captures pre-ESOP Adjusted EBITDA (₹1,200.5M) due to a detached table footnote on page 45, while Fact B reflects post-ESOP Adjusted EBITDA (₹720.0M). Context reconciles the exact delta (₹480.5M non-cash share-based expense).",
            "confidence": 0.94
        }
    ]

    for rec in reconciliations:
        storage.insert_reconciliation(rec)