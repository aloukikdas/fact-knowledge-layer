# OmniFact AI: Document Reconciliation Engine

OmniFact AI is a Fact Knowledge Layer built for the Built for the **Superjoin Campus Connect** Assignment. It extracts atomic corporate facts from dense financial PDFs, grounds them in verbatim evidence, and evaluates their relationships across documents to find corroborations, context-based reconciliations, and direct contradictions.

## Setup and Run Instructions

### 1. Prerequisites
* Python 3.10+
* A Google Gemini API Key ([Google AI Studio](https://aistudio.google.com/))

### 2. Installation
```bash
git clone <your-repo-link>
cd fact-knowledge-layer
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
### 3. Environment Variables
Create a .env file in the root directory and add your API key:
```code
GEMINI_API_KEY="your_api_key_here"
DATABASE_PATH="knowledge_layer.db"
UPLOAD_DIR="starter-datasets"
GEMINI_MODEL="chose_a_suitable_model_here"
```

### 4. Run Test Suite
Verify all storage contracts, extraction models, arbiter logic, and API endpoints:
```Bash
python run_all_tests.py
```
### 5. Run the Application
```Bash
uvicorn app.main:app --reload
```
Navigate to http://127.0.0.1:8000 to access the Audit Console.

---

## 🎥 Video Demo
Watch the 3-Minute Demo Video Here

The demo showcases the incremental ingestion of three starter PDFs and the successful extraction and arbitration of the four required evaluation cases.

---

## Approach
### 1. Architecture & Trade-offs
* **Fail-Safe Extraction Pipeline**: Instead of sending 300+ pages directly to an LLM (which hits rate limits and dilutes context), the system uses `PyMuPDF` to deterministically score and filter pages based on keyword density and numerical presence. Only the highest-signal pages are batched into a single LLM request per document.

* **Data Contracts**: I used `Pydantic` Structured Outputs to enforce a strict schema (`entity`, `canonical_metric`, `value`, `context_notes`). This ensures the LLM returns predictable JSON, mapping variants like "Rev Ops" or "Revenue" to a strict `revenue_from_operations key`.

* **Storage & Incremental Ingestion**: A `SQLite` knowledge base tracks document hashes. If new filings are uploaded, the system only extracts the new facts and incrementally reconciles them against the existing database without requiring a full rebuild.

### 2. The Four Cases

* **Corroborated**: Detected an entity status transition where the CIN's prefix updated from `U` (Unlisted in the prospectus) to `L` (Listed in the annual report).

* **Reconciled**: Revenue figures varied massively, but the engine parsed the temporal scope (a 9-month stub period vs. a 12-month fiscal year) to reconcile the difference safely.

* **Contradiction**: Detected conflicting values for "Pin codes covered" associated with the exact same temporal reporting date, flagging a genuine contradiction.

* **Edge Case / Extraction Failure Handled**: Table formatting in the PDFs pushed vital non-cash ESOP deductions into detached footnotes. I engineered the PyMuPDF parser to specifically scrape the bottom 35% bounding box of every page, appending these footnotes as context so the LLM could reconcile the Adjusted EBITDA variance.

---

## Limitations and Next Steps
* **PDF Table Garbage Characters**: The biggest limitation encountered was invisible whitespace injected by PDF table layouts (e.g., reading `17,500` as `17` and `500`). While I implemented robust regex fallbacks and normalization logic to patch this, standard text parsing remains brittle for complex financial tables.

* **Next Step (Vision-Language Models)**: If I were to push this to production, I would replace `PyMuPDF` text extraction with a Vision-Language Model (VLM) or Table Transformer (like Microsoft's Table-DETR) to process pages as images, preserving the structural integrity of multi-column financial disclosures.
---
## Additional Notes
**Brownie Points Achieved**: The system handles incremental ingestion (you can upload one PDF, then upload another later, and it will cross-check them dynamically) and uses batched LLM calls to process large PDFs rapidly without triggering 429 RESOURCE_EXHAUSTED quotas.

---

## 👨‍💻 Author

**Aloukik Das**
* **GitHub:** [https://github.com/aloukikdas](https://github.com/aloukikdas)
* **LinkedIn:** [https://www.linkedin.com/in/aloukik-das-0a8685304](https://www.linkedin.com/in/aloukik-das-0a8685304)
* **Project Link:** [https://github.com/aloukikdas/fact-knowledge-layer](https://github.com/aloukikdas/fact-knowledge-layer)
* **Demo Video:** []()


## 📝 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
