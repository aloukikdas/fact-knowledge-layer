import os
import json
import time
import uuid
from typing import List, Dict, Any, Optional, Tuple
from google import genai
from google.genai import types
from dotenv import load_dotenv

from app.models import Fact, CrossDocumentRelation, RelationshipType

load_dotenv()

ARBITER_SYSTEM_INSTRUCTION = """
You are a lead forensic financial analyst and IPO auditor.
Your job is to compare two facts extracted from different corporate/financial documents and determine their exact relationship.

CATEGORIES:
1. CORROBORATED: Both facts state the same truth or equivalent values (even if worded differently).
2. RECONCILED: The numbers or claims appear contradictory, BUT context cleanly explains the difference (e.g., different time periods, 9-month stub vs 12-month fiscal year, Consolidated vs Standalone, Restated Ind AS vs Reported, or explanatory footnotes).
3. CONTRADICTION: Both facts refer to the exact same metric, period, entity, and scope, but present conflicting values with NO valid reconciling explanation.
4. EDGE_CASE: A failure or nuance in extraction, such as detached footnotes, ambiguous units, or wording that requires specific post-processing.

Output a valid JSON object with keys: "relation" (one of the 4 above), "explanation", "confidence".
"""


class ReconciliationEngine:
    FALLBACK_MODELS = [
        os.getenv("GEMINI_MODEL", "gemini-3.6-flash"),
        "gemini-2.0-flash",
        "gemini-1.5-flash",
    ]

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not set.")
        
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = self.FALLBACK_MODELS[0]

    def _normalize_metric(self, metric: str) -> str:
        """Strips noise words to cluster related metrics."""
        m = metric.lower().replace("-", "_").replace(" ", "_")
        for prefix in ["total_", "consolidated_", "annual_"]:
            if m.startswith(prefix):
                m = m[len(prefix):]
        return m

    def cluster_facts(self, facts: List[Fact]) -> Dict[str, List[Fact]]:
        """Clusters facts across all documents by entity and normalized metric."""
        clusters: Dict[str, List[Fact]] = {}
        for f in facts:
            key = f"{f.entity.lower()}::{self._normalize_metric(f.canonical_metric)}"
            if key not in clusters:
                clusters[key] = []
            clusters[key].append(f)
        return clusters

    def _deterministic_evaluate(self, fact_a: Fact, fact_b: Fact) -> Tuple[RelationshipType, str, float]:
        """Rules-based semantic arbiter used as a fallback if LLM endpoints are throttled."""
        val_a_str = str(fact_a.value).strip().lower()
        val_b_str = str(fact_b.value).strip().lower()

        # 1. Exact value match
        if val_a_str == val_b_str:
            return (
                RelationshipType.CORROBORATED,
                f"Both filings corroborate the identical figure ({fact_a.value} {fact_a.unit or ''}) for {fact_a.raw_metric}.",
                0.98
            )

        # 2. Footnote / edge case detection
        notes_a = (fact_a.context_notes or "").lower()
        notes_b = (fact_b.context_notes or "").lower()
        raw_b = (fact_b.raw_metric or "").lower()

        if any(term in notes_a or term in notes_b for term in ["footnote", "detached", "exclusion", "esop"]) or "esop" in raw_b:
            return (
                RelationshipType.EDGE_CASE,
                "Extraction edge case identified: Discrepancy explained by detached/qualifying footnote adjustments (e.g. non-cash ESOP charges).",
                0.91
            )

        # 3. Contextual discrepancy (Periods, Scopes, or Accounting Standards differ)
        period_a = (fact_a.period or "").strip().lower()
        period_b = (fact_b.period or "").strip().lower()
        scope_a = (fact_a.scope or "consolidated").strip().lower()
        scope_b = (fact_b.scope or "consolidated").strip().lower()
        std_a = (fact_a.accounting_standard or "").strip().lower()
        std_b = (fact_b.accounting_standard or "").strip().lower()

        period_differs = period_a != period_b and period_a and period_b and period_a != "permanent"
        scope_differs = scope_a != scope_b and scope_a and scope_b
        std_differs = std_a != std_b and std_a and std_b

        if period_differs or scope_differs or std_differs:
            reasons = []
            if period_differs:
                reasons.append(f"time periods differ ('{fact_a.period}' vs '{fact_b.period}')")
            if scope_differs:
                reasons.append(f"reporting scopes differ ('{fact_a.scope}' vs '{fact_b.scope}')")
            if std_differs:
                reasons.append(f"standards differ ('{fact_a.accounting_standard}' vs '{fact_b.accounting_standard}')")
            return (
                RelationshipType.RECONCILED,
                f"Apparent contradiction reconciled by context: {', '.join(reasons)}.",
                0.93
            )

        # 4. Same entity, metric, period, and scope with conflicting values
        return (
            RelationshipType.CONTRADICTION,
            f"Genuine contradiction identified: Conflicting values ({fact_a.value} vs {fact_b.value}) reported for the same temporal period ('{fact_a.period}') and scope without reconciling disclosures.",
            0.95
        )

    def arbitrate_pair(self, fact_a: Fact, fact_b: Fact) -> Optional[CrossDocumentRelation]:
        """Determines the cross-document relationship between two facts."""
        if fact_a.provenance.document_name == fact_b.provenance.document_name:
            return None

        prompt = f"""
FACT A:
- Document: {fact_a.provenance.document_name} (Page {fact_a.provenance.page_number})
- Metric: {fact_a.raw_metric} (Canonical: {fact_a.canonical_metric})
- Value: {fact_a.value} {fact_a.unit or ''}
- Period: {fact_a.period or 'Not specified'}
- Scope: {fact_a.scope or 'Consolidated'}
- Accounting Standard: {fact_a.accounting_standard or 'N/A'}
- Context/Footnotes: {fact_a.context_notes or 'None'}
- Evidence: "{fact_a.provenance.evidence_quote}"

FACT B:
- Document: {fact_b.provenance.document_name} (Page {fact_b.provenance.page_number})
- Metric: {fact_b.raw_metric} (Canonical: {fact_b.canonical_metric})
- Value: {fact_b.value} {fact_b.unit or ''}
- Period: {fact_b.period or 'Not specified'}
- Scope: {fact_b.scope or 'Consolidated'}
- Accounting Standard: {fact_b.accounting_standard or 'N/A'}
- Context/Footnotes: {fact_b.context_notes or 'None'}
- Evidence: "{fact_b.provenance.evidence_quote}"

Task:
Determine whether Fact A and Fact B represent:
1. CORROBORATED
2. RECONCILED
3. CONTRADICTION
4. EDGE_CASE

Return JSON with keys: "relation" (one of the 4 above), "explanation", "confidence".
"""

        # Try models in fallback chain with a brief sleep retry on 503
        for model in self.FALLBACK_MODELS:
            for attempt in range(2):
                try:
                    response = self.client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=ARBITER_SYSTEM_INSTRUCTION,
                            response_mime_type="application/json",
                            temperature=0.1,
                        ),
                    )

                    res_json = json.loads(response.text)
                    rel_str = res_json.get("relation", "RECONCILED").upper()
                    
                    try:
                        rel_enum = RelationshipType(rel_str)
                    except ValueError:
                        rel_enum = RelationshipType.RECONCILED

                    self.model_name = model
                    return CrossDocumentRelation(
                        relation_id=f"rel_{uuid.uuid4().hex[:8]}",
                        fact_a=fact_a,
                        fact_b=fact_b,
                        relation=rel_enum,
                        explanation=res_json.get("explanation", "Context evaluated across filings."),
                        confidence=float(res_json.get("confidence", 0.9))
                    )
                except Exception as e:
                    err_msg = str(e)
                    if "503" in err_msg or "429" in err_msg:
                        time.sleep(1.5)  # Back off before retrying
                        continue
                    break

        # If external API is completely congested, fall back to deterministic semantic arbiter
        rel_type, explanation, confidence = self._deterministic_evaluate(fact_a, fact_b)
        return CrossDocumentRelation(
            relation_id=f"rel_{uuid.uuid4().hex[:8]}",
            fact_a=fact_a,
            fact_b=fact_b,
            relation=rel_type,
            explanation=explanation,
            confidence=confidence
        )

    def reconcile_all(self, facts: List[Fact]) -> List[CrossDocumentRelation]:
        """Runs clustered pairing and arbitration across all facts."""
        clusters = self.cluster_facts(facts)
        relations: List[CrossDocumentRelation] = []
        compared_pairs = set()

        for cluster_key, cluster_facts in clusters.items():
            if len(cluster_facts) < 2:
                continue

            for i in range(len(cluster_facts)):
                for j in range(i + 1, len(cluster_facts)):
                    fa = cluster_facts[i]
                    fb = cluster_facts[j]

                    if fa.provenance.document_name == fb.provenance.document_name:
                        continue

                    pair_id = tuple(sorted([fa.fact_id, fb.fact_id]))
                    if pair_id in compared_pairs:
                        continue
                    compared_pairs.add(pair_id)

                    relation = self.arbitrate_pair(fa, fb)
                    if relation:
                        relations.append(relation)

        return relations