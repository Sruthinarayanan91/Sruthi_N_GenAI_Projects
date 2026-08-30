from typing import List
from pydantic import BaseModel, Field

class CriterionEvaluation(BaseModel):
    criterion_id: int
    name: str
    score: float = Field(ge=0, le=10)
    max_score: float = Field(gt=0)
    justification: str
    evidence: str

class SupplierEvaluation(BaseModel):
    supplier_name: str
    criteria: List[CriterionEvaluation]
    risks: List[str] = []
    overall_summary: str
