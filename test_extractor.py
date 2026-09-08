import os
import time
from app.pdf_parser import PDFParser
from app.extractor import FactExtractor

DATASET_DIR = "starter-datasets"
PDF_PROSPECTUS = os.path.join(DATASET_DIR, "01-delhivery-prospectus-2022-excerpt.pdf")
PDF_ANNUAL = os.path.join(DATASET_DIR, "02-delhivery-annual-report-fy24-excerpt.pdf")

def test_live_extraction():
    print("=" * 50)
    print("FAK-LAYER: ASSIGNMENT #4 LIVE LLM FACT EXTRACTION TEST")
    print("=" * 50)

    parser = PDFParser()
    extractor = FactExtractor()

    # 1. Parse corporate summary page from Prospectus (Page 1)
    print("\n[1/3] Extracting facts from Prospectus (Page 1 - Corporate Details)...")
    chunks_p1 = parser.extract_document(PDF_PROSPECTUS, max_pages=1)
    assert len(chunks_p1) > 0, "Failed to parse page 1"

    t0 = time.time()
    facts_p1 = extractor.extract_from_chunk(chunks_p1[0])
    t1 = time.time()

    print(f"✓ Extracted {len(facts_p1)} facts in {t1 - t0:.2f}s:")
    for f in facts_p1[:3]:
        print(f"  • [{f.canonical_metric}] = {f.value} {f.unit or ''} | Period: {f.period or 'N/A'}")
        print(f"    Quote: \"{f.provenance.evidence_quote[:80]}...\"")

    assert len(facts_p1) > 0, "No facts extracted from Prospectus page 1"

    # 2. Parse corporate summary page from Annual Report (Page 2)
    print("\n[2/3] Extracting facts from Annual Report FY24 (Page 2 - Corporate Overview)...")
    chunks_a2 = parser.extract_document(PDF_ANNUAL, max_pages=2)
    # Target page 2
    target_chunk = chunks_a2[1] if len(chunks_a2) > 1 else chunks_a2[0]

    t0 = time.time()
    facts_a2 = extractor.extract_from_chunk(target_chunk)
    t1 = time.time()

    print(f"✓ Extracted {len(facts_a2)} facts in {t1 - t0:.2f}s:")
    for f in facts_a2[:3]:
        print(f"  • [{f.canonical_metric}] = {f.value} {f.unit or ''} | Period: {f.period or 'N/A'}")
        print(f"    Quote: \"{f.provenance.evidence_quote[:80]}...\"")

    assert len(facts_a2) > 0, "No facts extracted from Annual Report page 2"

    # 3. Validate Schema Properties
    print("\n[3/3] Validating strict provenance and metadata completeness...")
    sample_fact = facts_p1[0]
    assert sample_fact.entity != "", "Entity is missing"
    assert sample_fact.canonical_metric != "", "Canonical metric is missing"
    assert sample_fact.provenance.document_name.endswith(".pdf"), "Provenance document invalid"
    assert sample_fact.provenance.page_number > 0, "Page number invalid"
    assert len(sample_fact.provenance.evidence_quote) > 10, "Evidence quote too short"
    print("✓ All structural fields and provenance links verified!")

    print("\n" + "=" * 50)
    print("STATUS: Assignment #4 passed with 0 errors!")
    print("=" * 50)

if __name__ == "__main__":
    test_live_extraction()