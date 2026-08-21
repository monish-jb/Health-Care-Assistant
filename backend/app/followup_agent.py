"""
Follow-Up Question & Interactive Option Chip Agent for Healthcare Knowledge Navigator.
Determines missing clinical information and generates targeted follow-up questions and quick-response chips.
"""

from typing import List, Tuple, Optional, Dict, Any
from app.models import PatientContext
from app.patient_context import format_patient_context_summary

CLINICAL_FOLLOWUP_MATRIX = {
    "fatigue": [
        {
            "condition": lambda ctx: not ctx.get("duration"),
            "question": "How long have you or your relative been experiencing this fatigue?",
            "options": ["1 week", "1 month", "3+ months", "Just a few days"]
        },
        {
            "condition": lambda ctx: not any(s in ctx.get("symptoms", []) for s in ["fever", "weight loss", "shortness of breath", "dizziness"]),
            "question": "Are there any accompanying symptoms present?",
            "options": ["Fever or night sweats", "Unexplained weight loss", "Shortness of breath", "Dizziness or weakness", "None of these"]
        },
        {
            "condition": lambda ctx: not ctx.get("age"),
            "question": "Could you share the approximate age of the person experiencing fatigue?",
            "options": ["Under 18", "18–40", "41–65", "Over 65"]
        }
    ],
    "headache": [
        {
            "condition": lambda ctx: not ctx.get("duration"),
            "question": "How long have these headaches been occurring?",
            "options": ["Few days", "1–2 weeks", "Over a month", "Chronic/Years"]
        },
        {
            "condition": lambda ctx: True,  # Frequency/Pattern check
            "question": "How frequently do the headaches occur and how would you describe the pain?",
            "options": ["Daily constant pain", "Throbbing on one side", "Pressure around forehead", "Intermittent sharp spikes"]
        },
        {
            "condition": lambda ctx: not any(s in ctx.get("symptoms", []) for s in ["nausea", "stiff neck", "fever", "vision changes"]),
            "question": "Are you experiencing any accompanying symptoms?",
            "options": ["Nausea or sensitivity to light", "Fever or stiff neck", "Vision changes", "None of these"]
        }
    ],
    "stomach pain": [
        {
            "condition": lambda ctx: True,
            "question": "Where exactly is the stomach pain located?",
            "options": ["Upper abdomen", "Lower right abdomen", "Lower left abdomen", "All over/Generalized"]
        },
        {
            "condition": lambda ctx: not ctx.get("duration"),
            "question": "When did the abdominal pain start?",
            "options": ["Suddenly today", "Past 2–3 days", "Over a week ago", "Recurring for months"]
        },
        {
            "condition": lambda ctx: not any(s in ctx.get("symptoms", []) for s in ["vomiting", "fever", "diarrhea", "blood in stool"]),
            "question": "Are there any associated symptoms?",
            "options": ["Nausea or vomiting", "Fever or chills", "Diarrhea or constipation", "None of these"]
        }
    ],
    "cough": [
        {
            "condition": lambda ctx: not ctx.get("duration"),
            "question": "How long has the cough been present?",
            "options": ["Less than 1 week", "1–3 weeks", "More than 3 weeks"]
        },
        {
            "condition": lambda ctx: True,
            "question": "Is the cough dry or producing mucus/phlegm?",
            "options": ["Dry cough", "Clear/White phlegm", "Yellow/Green phlegm", "Blood-tinged"]
        }
    ]
}

def evaluate_missing_clinical_context(intent: str, ctx: PatientContext) -> Tuple[bool, Optional[str], Optional[List[str]]]:
    """
    Evaluates if critical context is missing for a symptom query.
    Returns (should_ask_followup, followup_question_text, option_chips_list).
    """
    # Only ask follow-ups for symptom queries or initial general symptom descriptions
    if intent not in ["symptom_question", "general_health_question"]:
        return False, None, None

    ctx_dict = format_patient_context_summary(ctx)
    symptoms = ctx_dict.get("symptoms", [])

    # Match primary symptom matrix
    for sym_key, rules in CLINICAL_FOLLOWUP_MATRIX.items():
        if any(sym_key in s for s in symptoms) or sym_key in ctx.symptoms.lower():
            for rule in rules:
                if rule["condition"](ctx_dict):
                    return True, rule["question"], rule["options"]

    # Generic symptom missing duration check if symptoms exist but duration is missing
    if symptoms and not ctx_dict.get("duration"):
        return (
            True,
            f"To help provide relevant medical information regarding {', '.join(symptoms)}, how long have these symptoms been present?",
            ["1–3 days", "1–2 weeks", "1 month", "More than 1 month"]
        )

    # Generic symptom missing age check
    if symptoms and not ctx_dict.get("age"):
        return (
            True,
            "Could you share your approximate age (or the patient's age)? Age can significantly influence potential health considerations.",
            ["Child (<18)", "Adult (18-64)", "Senior (65+)"]
        )

    return False, None, None
