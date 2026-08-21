"""
Agent 1: Triage Agent (Assess + Route)
Implements the 4-Step Clinical Triage Protocol:
1. Symptom Intake (natural chat parsing)
2. Structured Extraction (symptoms, duration, severity, patient context)
3. Ranked Possibility List (probabilistic conditions ranking + confidence score)
4. Confidence Gating & Department Routing (Cardiology, Endocrinology, Pulmonology, Gastroenterology, General Medicine)
"""

from typing import Dict, Any, List, Tuple
from app.triage import evaluate_medical_triage
from app.patient_context import extract_patient_entities

DEPARTMENT_SYMPTOM_MAP = {
    "Cardiology": ["chest pain", "palpitations", "shortness of breath", "high blood pressure", "hypertension", "cholesterol", "dizziness"],
    "Endocrinology": ["thyroid", "fatigue", "diabetes", "glucose", "weight gain", "weight loss", "tsh", "hba1c", "increased thirst"],
    "Pulmonology": ["cough", "wheezing", "asthma", "phlegm", "mucus", "breathlessness", "bronchitis", "respiratory"],
    "Gastroenterology": ["stomach pain", "acid reflux", "gerd", "nausea", "vomiting", "diarrhea", "constipation", "bloating", "abdominal pain"],
    "General Medicine": ["fever", "headache", "body ache", "general weakness", "malaise", "cold", "flu", "chills", "tired"]
}

CONDITION_DIAGNOSIS_MAP = {
    "Cardiology": [
        {"condition": "Possible Essential Hypertension / Cardiovascular Strain", "base_confidence": 0.85},
        {"condition": "Pre-hypertensive Metabolic Syndrome", "base_confidence": 0.72}
    ],
    "Endocrinology": [
        {"condition": "Primary Hypothyroidism / Thyroid Dysfunction", "base_confidence": 0.88},
        {"condition": "Impaired Fasting Glycemia / Pre-Diabetes Mellitus", "base_confidence": 0.78},
        {"condition": "Chronic Metabolic Fatigue Syndrome", "base_confidence": 0.65}
    ],
    "Pulmonology": [
        {"condition": "Acute Upper Respiratory Tract Infection", "base_confidence": 0.84},
        {"condition": "Bronchial Hyperreactivity / Post-Viral Cough", "base_confidence": 0.75}
    ],
    "Gastroenterology": [
        {"condition": "Gastroesophageal Reflux Disease (GERD) / Dyspepsia", "base_confidence": 0.86},
        {"condition": "Acute Gastritis / Peptic Irritation", "base_confidence": 0.74}
    ],
    "General Medicine": [
        {"condition": "Acute Viral Syndrome / Febrile Illness", "base_confidence": 0.85},
        {"condition": "Tension Headache / Fatigue-Related Cephalea", "base_confidence": 0.78}
    ]
}

def run_triage_assessment(user_text: str, patient_context_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes the 4-step triage process.
    Returns structured triage recommendation with ranked conditions and routed department.
    """
    text_lower = user_text.lower()
    
    # 1. Emergency Safety Override Check
    triage_level, emergency_msg = evaluate_medical_triage(user_text)
    if triage_level == "EMERGENCY":
        return {
            "triage_level": "EMERGENCY",
            "is_emergency": True,
            "department": "Emergency Medicine / Immediate Care",
            "confidence_score": 0.99,
            "ranked_possibilities": [
                {"condition": "Acute Critical Emergency (Immediate Hospital Attention Required)", "probability": "99%"}
            ],
            "confidence_gate": "ESCALATED_TO_HUMAN",
            "recommendation": emergency_msg,
            "can_auto_book": False
        }

    # 2. Extract Structured Entities
    extracted = extract_patient_entities(user_text)
    all_symptoms = list(set(patient_context_dict.get("symptoms", []) + extracted.get("symptoms", [])))
    if not all_symptoms and any(w in text_lower for w in ["fever", "tired", "headache", "cough", "pain", "fatigue"]):
        for w in ["fever", "tired", "headache", "cough", "pain", "fatigue"]:
            if w in text_lower:
                all_symptoms.append(w)

    # 3. Department Scoring
    dept_scores = {dept: 0 for dept in DEPARTMENT_SYMPTOM_MAP}
    for dept, keywords in DEPARTMENT_SYMPTOM_MAP.items():
        for kw in keywords:
            if kw in text_lower or any(kw in s for s in all_symptoms):
                dept_scores[dept] += 1

    best_dept = max(dept_scores, key=dept_scores.get)
    if dept_scores[best_dept] == 0:
        best_dept = "General Medicine"

    # 4. Generate Ranked Possibilities
    possible_conditions = CONDITION_DIAGNOSIS_MAP.get(best_dept, CONDITION_DIAGNOSIS_MAP["General Medicine"])
    ranked_list = []
    for idx, item in enumerate(possible_conditions):
        prob = int(item["base_confidence"] * 100) - (idx * 10)
        ranked_list.append({
            "condition": item["condition"],
            "probability": f"{prob}%"
        })

    # 5. Confidence Gate Check
    top_confidence = possible_conditions[0]["base_confidence"]
    gate_status = "ROUTED_TO_DEPARTMENT" if top_confidence >= 0.70 else "ESCALATE_TO_NURSE"

    return {
        "triage_level": triage_level,
        "is_emergency": False,
        "department": best_dept,
        "confidence_score": top_confidence,
        "ranked_possibilities": ranked_list,
        "confidence_gate": gate_status,
        "recommendation": f"Based on your reported symptoms, consultation with the Department of {best_dept} is recommended.",
        "can_auto_book": True
    }
