import os
import fitz  # PyMuPDF
from dotenv import load_dotenv

load_dotenv()

def verify():
    print("=" * 50)
    print("FAK-LAYER: ENVIRONMENT VERIFICATION")
    print("=" * 50)

    # 1. Check Python Dependencies
    print("[1/3] Checking core dependencies...")
    try:
        import fastapi
        import pydantic
        import uvicorn
        print(f"  ✓ FastAPI: {fastapi.__version__}")
        print(f"  ✓ Pydantic: {pydantic.__version__}")
        print(f"  ✓ PyMuPDF: {fitz.__version__}")
    except ImportError as e:
        print(f"  ✗ Import error: {e}")
        return False

    # 2. Check PDFs in starter-datasets
    print("\n[2/3] Verifying starter datasets...")
    dataset_dir = "starter-datasets"
    if not os.path.exists(dataset_dir):
        print(f"  ✗ Folder '{dataset_dir}' does not exist.")
        return False

    pdf_files = [f for f in os.listdir(dataset_dir) if f.endswith(".pdf")]
    if not pdf_files:
        print(f"  ✗ No PDF files found in '{dataset_dir}'. Please copy them over.")
        return False

    for pdf in pdf_files:
        path = os.path.join(dataset_dir, pdf)
        try:
            doc = fitz.open(path)
            print(f"  ✓ Found '{pdf}' | Pages: {len(doc)}")
            doc.close()
        except Exception as e:
            print(f"  ✗ Could not open '{pdf}': {e}")
            return False

    # 3. Check Gemini API Key
    print("\n[3/3] Checking API key configuration...")
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key or "YOUR_GEMINI" in api_key:
        print("  ! Warning: GEMINI_API_KEY is not set or using placeholder in .env.")
        print("    (You can add this before Assignment #4, but keep it in mind.)")
    else:
        print(f"  ✓ GEMINI_API_KEY detected (starts with '{api_key[:6]}...')")

    print("\n" + "=" * 50)
    print("STATUS: Setup looks solid! Ready for Assignment #2.")
    print("=" * 50)
    return True

if __name__ == "__main__":
    verify()