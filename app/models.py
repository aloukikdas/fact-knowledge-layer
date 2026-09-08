from enum import Enum
from typing import Optional, List, Union
from pydantic import BaseModel, Field

class RelationshipType(str, Enum):
    CORROBORATED = "CORROBORATED"
    CONTRADICTION = "CONTRADICTION"
    RECONCILED = "RECONCILED"
    EDGE_CASE = "EDGE_CASE"

class Provenance(BaseModel):
    document_name: str = Field(..., description="Filename of the source PDF")
    page_number: int = Field(..., description="1-based page number where evidence is found")
    evidence_quote: str = Field(..., description="Exact textual quote or table snippet from the source")

class Fact(BaseModel):
    fact_id: Optional[str] = Field(None, description="Unique ID for this fact")
    entity: str = Field(default="Delhivery Limited", description="Target corporate entity")
    canonical_metric: str = Field(..., description="Standardized metric name in snake_case")
    raw_metric: str = Field(..., description="Original metric text as phrased in the PDF")
    value: Union[float, int, str] = Field(..., description="Numerical figure or discrete attribute value")
    unit: Optional[str] = Field(None, description="Currency or metric unit")
    period: Optional[str] = Field(None, description="Temporal scope")
    scope: Optional[str] = Field("Consolidated", description="Scope of reporting")
    accounting_standard: Optional[str] = Field(None, description="Accounting standard used")
    context_notes: Optional[str] = Field(None, description="Footnotes, exclusions, or qualifying context")
    provenance: Provenance

# This is the class your server was failing to import
class FactExtractionResponse(BaseModel):
    facts: List[Fact] = Field(default_factory=list, description="List of extracted grounded facts")

class CrossDocumentRelation(BaseModel):
    relation_id: Optional[str] = None
    fact_a: Fact
    fact_b: Fact
    relation: RelationshipType
    explanation: str = Field(..., description="Detailed analytical justification for this classification")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score of classification")

ReconciliationResult = CrossDocumentRelation