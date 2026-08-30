import json
from openai import OpenAI
from app.models.evaluation_models import SupplierEvaluation
from app.services.scoring_service import validate_evaluation

def evaluate_supplier(pdf_text, criteria_text, active_criteria, client: OpenAI, model_name: str):
    prompt = f"""
You are an RFP Evaluation Agent.
Evaluate the supplier proposal against ALL active evaluation criteria.
Use ONLY information contained in the supplier proposal. Do not invent facts.

Return ONLY valid JSON in exactly this structure:
{{
  "supplier_name": "string",
  "criteria": [
    {{
      "criterion_id": 1,
      "name": "string",
      "score": 0,
      "max_score": 10,
      "justification": "string",
      "evidence": "string"
    }}
  ],
  "risks": ["string"],
  "overall_summary": "string"
}}

Rules:
- Evaluate EVERY active criterion.
- score must be between 0 and the criterion maximum.
- Evidence must come from the proposal; if unavailable say so.
- Do not calculate weighted scores, PPI, or rank.

ACTIVE CRITERIA:
{criteria_text}

SUPPLIER PROPOSAL:
{pdf_text}
"""
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role":"system","content":"You are a careful procurement evaluation agent. Return only valid JSON."},
            {"role":"user","content":prompt}
        ],
        response_format={"type":"json_object"},
    )
    data = json.loads(response.choices[0].message.content)
    evaluation = SupplierEvaluation.model_validate(data)
    validate_evaluation(evaluation, active_criteria)
    return evaluation
