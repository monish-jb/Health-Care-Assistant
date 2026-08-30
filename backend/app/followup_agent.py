"""
Medical Intake Assistant Agent for Healthcare Knowledge Navigator.
Evaluates the patient context state and returns missing clinical fields.
Does NOT return any user-facing text, questions, or option chips.
"""

from typing import List, Tuple, Dict, Any
from app.models import PatientContext
from app.patient_context import format_patient_context_summary

def evaluate_missing_clinical_context(intent: str, ctx: PatientContext) -> Tuple[List[str], bool]:
    """
    Evaluates missing clinical intake fields based on PatientContext state.
    Returns (missing_fields_list, has_emergency_red_flags).
    """
    ctx_dict = format_patient_context_summary(ctx)

    if ctx.intake_completed:
        return [], False

    missing_fields = []

    # Step 1: primary_complaint
    if not ctx.primary_complaint:
        missing_fields.append("primary_complaint")

    # Step 2: duration
    if not ctx_dict.get("duration"):
        missing_fields.append("duration")

    # Step 3: onset_pattern
    if not ctx_dict.get("onset_pattern"):
        missing_fields.append("onset_pattern")

    # Step 4: associated_symptoms
    symptoms_list = ctx_dict.get("symptoms", [])
    if len(symptoms_list) <= 1:
        missing_fields.append("associated_symptoms")

    # Step 5: severity
    if not ctx_dict.get("severity"):
        missing_fields.append("severity")

    # Step 6: known_conditions
    conds = ctx_dict.get("known_conditions", [])
    if not conds or len(conds) == 0:
        missing_fields.append("known_conditions")

    # Step 7: medications
    meds = ctx_dict.get("medications", [])
    if not meds or len(meds) == 0:
        missing_fields.append("medications")

    # Step 8: allergies
    if not ctx_dict.get("allergies"):
        missing_fields.append("allergies")

    # Step 9: recent_exposure
    if not ctx_dict.get("recent_exposure"):
        missing_fields.append("recent_exposure")

    # Step 10: safety check / red flags
    if ctx.current_step < 10:
        missing_fields.append("safety_red_flags")

    # If step is past 10, mark complete
    if ctx.current_step > 10:
        ctx.intake_completed = True
        return [], False

    return missing_fields, False
