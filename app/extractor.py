import os
import json
import uuid
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from google import genai
from google.genai import types

from app.models import Fact, Provenance, FactExtractionResponse
from app.pdf_parser import PageChunk

load_dotenv()


EXTRACTION_SYSTEM_INSTRUCTION = """
You are a senior financial analyst and document intelligence specialist for an IPO readiness platform.
Your objective is to extract atomic, meaningful financial, operational, and corporate facts from document page chunks.

CRITICAL EXTRACTION GUIDELINES:
1. ONLY extract facts that are directly supported by the text or tables on this page.
2. For every fact, extract:
   - entity: The legal company or person (e.g., "Delhivery Limited", "Sahil Barua").
   - canonical_metric: Standardized snake_case identifier (e.g., "revenue_from_operations", "ebitda", "incorporation_date", "registered_office", "pin_codes_covered", "active_customers").
   - raw_metric: The exact label as written in the text or table header.
   - value: The exact number or string value.
   - unit: Currency or metric unit (e.g., "INR Million", "INR Cr", "Count", "Percentage", "N/A").
   - period: The exact temporal duration or anchor (e.g., "FY 2021 (12 Months ended March 31, 2021)", "9M ended Dec 31, 2021", "FY 2023-24"). If not applicable, use "Permanent/Current".
   - scope: "Consolidated", "Standalone", or specific subsidiary name.
   - accounting_standard: "Restated Ind AS", "Audited Ind AS", or "N/A".
   - context_notes: Crucial footnote references, exclusions, adjustments, or qualifying context attached to this value.
   - evidence_quote: An exact, verbatim excerpt from the page proving this fact.

Prioritize:
- Key Financials (Revenue, Profit/Loss, EBITDA, Borrowings, Total Assets)
- Corporate Details (Incorporation date, CIN, Registered Office, Founders/Directors)
- Operational Scale (PIN codes covered, Automated Sort Centers, Fleet/Hub counts, Volume)
"""


class FactExtractor:
    FALLBACK_MODELS = [
        os.getenv("GEMINI_MODEL", "gemini-3.6-flash"),
        "gemini-2.0-flash",
        "gemini-1.5-flash",
    ]

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set in environment or .env file.")
        
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = self.FALLBACK_MODELS[0]

    def extract_from_chunk(self, chunk: PageChunk) -> List[Fact]:
        """Extracts structured facts from a single PageChunk, trying fallback models if needed."""
        footnotes_formatted = "\n".join(f"- {fn}" for fn in chunk.footnotes) if chunk.footnotes else "None"
        
        prompt = f"""
DOCUMENT: {chunk.document_name}
PAGE NUMBER: {chunk.page_number}

FOOTNOTES / CONTEXTUAL NOTES FOUND ON THIS PAGE:
{footnotes_formatted}

PAGE CONTENT:
---
{chunk.text}
---

Extract all distinct, verifiable facts from the content above. If no concrete numerical or corporate facts are present, return an empty list.
"""

        for model in self.FALLBACK_MODELS:
            try:
                response = self.client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=EXTRACTION_SYSTEM_INSTRUCTION,
                        response_mime_type="application/json",
                        response_schema=FactExtractionResponse,
                        temperature=0.1,
                    ),
                )
                
                raw_json = json.loads(response.text)
                extracted_facts: List[Fact] = []

                for item in raw_json.get("facts", []):
                    fact_id = item.get("fact_id") or f"fact_{uuid.uuid4().hex[:8]}"
                    
                    provenance_data = item.get("provenance", {})
                    provenance = Provenance(
                        document_name=chunk.document_name,
                        page_number=chunk.page_number,
                        evidence_quote=provenance_data.get("evidence_quote") or chunk.text[:150]
                    )

                    fact = Fact(
                        fact_id=fact_id,
                        entity=item.get("entity", "Delhivery Limited"),
                        canonical_metric=item.get("canonical_metric", "unknown_metric").lower().strip(),
                        raw_metric=item.get("raw_metric", "Metric"),
                        value=item.get("value", ""),
                        unit=item.get("unit"),
                        period=item.get("period"),
                        scope=item.get("scope", "Consolidated"),
                        accounting_standard=item.get("accounting_standard"),
                        context_notes=item.get("context_notes"),
                        provenance=provenance
                    )
                    extracted_facts.append(fact)

                # Set active model if fallback succeeded
                self.model_name = model
                return extracted_facts

            except Exception as e:
                print(f"Extraction attempt with {model} failed on {chunk.document_name} pg {chunk.page_number}: {e}")
                continue

        return []

    def process_chunks(self, chunks: List[PageChunk], max_facts_per_doc: int = 50) -> List[Fact]:
        """Runs extraction across a list of page chunks."""
        all_facts: List[Fact] = []
        for chunk in chunks:
            facts = self.extract_from_chunk(chunk)
            all_facts.extend(facts)
            if len(all_facts) >= max_facts_per_doc:
                break
        return all_facts