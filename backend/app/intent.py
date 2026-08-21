"""
Healthcare Intent Detection Module for Healthcare Knowledge Navigator.
Classifies user queries into medical intent categories.
"""

import re
from typing import Tuple

HEALTH_INTENT_KEYWORDS = {
    "emergency_symptoms": [
        "chest pain", "shortness of breath", "bleeding", "unconscious", "passed out",
        "stroke", "numbness", "severe pain", "throat closing", "emergency", "911"
    ],
    "lab_report_interpretation": [
        "blood test", "lab report", "hemoglobin", "tsh", "glucose", "wbc", "cholesterol",
        "creatinine", "test results", "blood report", "hba1c", "platelets", "triglycerides", "lipid panel"
    ],
    "medication_question": [
        "medication", "medicine", "drug", "pill", "ibuprofen", "paracetamol", "side effect",
        "dosage", "take with", "interaction", "supplement", "antibiotic", "statin", "metformin"
    ],
    "prescription_explanation": [
        "prescription", "prescribed", "rx", "refill", "doctor prescribed", "pharmacy"
    ],
    "symptom_question": [
        "symptom", "feeling tired", "fatigue", "headache", "fever", "stomach pain", "nausea",
        "dizziness", "rash", "joint pain", "cough", "sore throat", "back pain", "cramps"
    ],
    "disease_information": [
        "diabetes", "hypertension", "cancer", "asthma", "arthritis", "covid", "flu",
        "pneumonia", "migraine", "anemia", "thyroid", "gerd", "disease", "condition", "disorder"
    ],
    "treatment_information": [
        "treatment", "cure", "therapy", "surgery", "remedy", "how to treat", "management"
    ],
    "prevention": [
        "prevent", "prevention", "vaccine", "vaccination", "avoid", "risk factors", "screening"
    ],
    "nutrition": [
        "diet", "nutrition", "vitamins", "food", "eat", "calories", "protein", "weight loss"
    ],
    "appointment_navigation": [
        "specialist", "doctor", "cardiologist", "dermatologist", "neurologist", "find a doctor",
        "appointment", "when to see a doctor", "clinic"
    ],
    "document_analysis": [
        "document", "pdf", "file", "attached report", "scan", "medical record", "chart"
    ],
    "complaint": [
        "complaint", "failed", "charged", "refund", "horrible", "terrible", "scam", "dispute", "support ticket", "escalate", "unsatisfied"
    ],
    "billing_dispute": [
        "billing", "payment", "charged twice", "subscription", "price", "invoice", "refund", "overcharge"
    ]
}

def classify_intent(text: str) -> Tuple[str, float]:
    """
    Classify user query into healthcare intent and calculate confidence score.
    Returns (intent_name, confidence_score).
    """
    text_lower = text.lower()
    scores = {}

    for intent, keywords in HEALTH_INTENT_KEYWORDS.items():
        match_count = sum(1 for kw in keywords if kw in text_lower)
        if match_count > 0:
            scores[intent] = match_count

    if not scores:
        return "general_health_question", 0.70

    best_intent = max(scores, key=scores.get)
    matches = scores[best_intent]

    if matches >= 3:
        confidence = 0.95
    elif matches == 2:
        confidence = 0.85
    else:
        confidence = 0.75

    return best_intent, round(confidence, 2)
