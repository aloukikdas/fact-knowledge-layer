import os
import time
from app.pdf_parser import PDFParser

DATASET_DIR = "starter-datasets"
PDF_1 = os.path.join(DATASET_DIR, "01-delhivery-prospectus-2022-excerpt.pdf")
PDF_2 = os.path.join(DATASET_DIR, "02-delhivery-annual-report-fy24-excerpt.pdf")

def test_pdf_parsing():
    print("=" * 50)
    print("FAK-LAYER: ASSIGNMENT #3 PDF PARSER TEST")
    print("=" * 50)

    parser = PDFParser()

    # 1. Parse sample pages from Prospectus (2022)
    print("\n[1/3] Parsing first 15 pages of Prospectus 2022...")
    t0 = time.time()
    chunks_1 = parser.extract_document(PDF_1, max_pages=15)
    t1 = time.time()
    print(f"✓ Parsed {len(chunks_1)} valid pages in {t1 - t0:.2f}s (Speed: {(t1 - t0)/15*1000:.1f}ms/page)")
    assert len(chunks_1) > 0, "No chunks extracted from Prospectus"
    
    sample_chunk = chunks_1[0]
    print(f"  • Sample Page: {sample_chunk.page_number}")
    print(f"  • Doc Name: {sample_chunk.document_name}")
    print(f"  • Character count: {sample_chunk.char_count}")

    # 2. Parse sample pages from Annual Report (FY24)
    print("\n[2/3] Parsing first 15 pages of Annual Report FY24...")
    t0 = time.time()
    chunks_2 = parser.extract_document(PDF_2, max_pages=15)
    t1 = time.time()
    print(f"✓ Parsed {len(chunks_2)} valid pages in {t1 - t0:.2f}s")
    assert len(chunks_2) > 0, "No chunks extracted from Annual Report"

    # 3. Test Footnote / Context Isolation
    print("\n[3/3] Scanning for footnote-aware isolation...")
    detected_footnotes = 0
    for c in chunks_1 + chunks_2:
        if c.footnotes:
            detected_footnotes += 1

    print(f"✓ Pages with successfully extracted footnote blocks: {detected_footnotes}")
    
    print("\n" + "=" * 50)
    print("STATUS: Assignment #3 passed with 0 errors!")
    print("=" * 50)

if __name__ == "__main__":
    test_pdf_parsing()