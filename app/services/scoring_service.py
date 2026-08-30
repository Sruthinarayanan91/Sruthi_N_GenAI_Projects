def validate_evaluation(evaluation, active_criteria):
    expected = set(active_criteria["criterion_id"].tolist())
    returned = {c.criterion_id for c in evaluation.criteria}
    missing = expected - returned
    extra = returned - expected
    if missing:
        raise ValueError(f"Missing evaluations: {missing}")
    if extra:
        raise ValueError(f"Unexpected criterion IDs: {extra}")
    max_scores = dict(zip(active_criteria["criterion_id"], active_criteria["max_score"]))
    for c in evaluation.criteria:
        m = float(max_scores[c.criterion_id])
        if not 0 <= c.score <= m:
            raise ValueError(f"Invalid score for {c.name}: {c.score}; max={m}")
    return True

def calculate_scorecard(evaluation, active_criteria):
    if abs(float(active_criteria["weight"].sum()) - 100) > 1e-9:
        raise ValueError("Criteria weights must sum to 100")
    lookup = {int(r["criterion_id"]): r for _, r in active_criteria.iterrows()}
    items, total = [], 0.0
    for c in evaluation.criteria:
        cfg = lookup[c.criterion_id]
        weight = float(cfg["weight"])
        max_score = float(cfg["max_score"])
        if not 0 <= c.score <= max_score:
            raise ValueError(f"Invalid score for {c.name}")
        weighted = float(c.score) * weight / 100
        total += weighted
        items.append({
            "criterion_id": c.criterion_id, "name": c.name,
            "score": float(c.score), "max_score": max_score,
            "weight": weight, "weighted_score": weighted,
            "justification": c.justification, "evidence": c.evidence
        })
    return {
        "supplier_name": evaluation.supplier_name,
        "criteria": items,
        "total_score": total,
        "percentage_score": total * 10,
        "risks": evaluation.risks,
        "overall_summary": evaluation.overall_summary,
    }

def calculate_ranking(scorecards):
    avg = sum(s["total_score"] for s in scorecards.values()) / len(scorecards)
    rows = [{
        "supplier_name": n,
        "weighted_score": s["total_score"],
        "percentage_score": s["total_score"] * 10,
        "ppi": s["total_score"] / avg if avg else 0
    } for n, s in scorecards.items()]
    rows.sort(key=lambda x: x["weighted_score"], reverse=True)
    for i, row in enumerate(rows, 1):
        row["rank"] = i
    return rows, avg
