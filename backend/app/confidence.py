"""
Deterministic Evidence Confidence Scoring Engine for Healthcare Knowledge Navigator.
Calculates evidence confidence using measurable signals (relevance, source quality, source count, agreement).
"""

from typing import List, Dict, Any, Tuple

SOURCE_QUALITY_WEIGHTS = {
    "Clinical Guideline": 1.0,
    "Health Authority": 0.9,
    "Research Paper": 0.85,
    "Clinical Reference": 0.75
}

def calculate_evidence_confidence(
    rag_results: List[Dict[str, Any]],
    query: str,
    kb_doc_count: int
) -> Tuple[str, Dict[str, Any]]:
    """
    Calculates evidence confidence based on measurable retrieval signals.
    Returns (confidence_level, confidence_details).
    Confidence levels: 'HIGH', 'MEDIUM', 'LOW'
    """
    if kb_doc_count == 0 or not rag_results:
        return "LOW", {
            "score": 0.0,
            "supporting_sources": 0,
            "top_relevance": 0.0,
            "source_agreement": "None",
            "explanation": "No matching clinical guidelines or evidence documents were found in the knowledge base."
        }

    top_relevance = rag_results[0].get("score", 0.0)
    supporting_sources = len(rag_results)

    # 1. Source quality score
    quality_scores = [
        SOURCE_QUALITY_WEIGHTS.get(r.get("source_type", "Clinical Reference"), 0.75)
        for r in rag_results
    ]
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.75

    # 2. Agreement score (consistency between top retrieved chunk scores)
    if len(rag_results) > 1:
        score_diff = abs(rag_results[0]["score"] - rag_results[1]["score"])
        if score_diff < 0.1:
            agreement_str = "Strong"
            agreement_bonus = 0.15
        elif score_diff < 0.25:
            agreement_str = "Moderate"
            agreement_bonus = 0.08
        else:
            agreement_str = "Limited"
            agreement_bonus = 0.0
    else:
        agreement_str = "Single Source"
        agreement_bonus = 0.05

    # Combined composite index score
    composite_score = (top_relevance * 0.5) + (avg_quality * 0.35) + agreement_bonus

    if composite_score >= 0.65 and top_relevance >= 0.45:
        level = "HIGH"
        explanation = f"High confidence. Supported by {supporting_sources} relevant source(s) with strong clinical alignment."
    elif composite_score >= 0.35 or top_relevance >= 0.25:
        level = "MEDIUM"
        explanation = f"Moderate confidence. {supporting_sources} reference document(s) retrieved. Further context may refine results."
    else:
        level = "LOW"
        explanation = "Low evidence confidence. Limited matching clinical documentation found. Advice should be interpreted with caution."

    details = {
        "score": round(composite_score, 3),
        "supporting_sources": supporting_sources,
        "top_relevance": round(top_relevance, 3),
        "source_agreement": agreement_str,
        "explanation": explanation
    }

    return level, details
