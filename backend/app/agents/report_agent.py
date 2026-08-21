"""
Agent 3: Report Agent (Doctor-Ready Draft Summaries)
Converts chat transcripts, patient context, and preliminary assessment into
a structured SOAP-style draft note with suggested preliminary tests for physician review.
"""

import json
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models import Conversation, Message, PatientContext, SOAPReport, User
from app.patient_context import format_patient_context_summary

SUGGESTED_TESTS_BY_DEPT = {
    "Cardiology": ["12-Lead Electrocardiogram (ECG)", "Lipid Profile Panel", "Serum Electrolytes", "Blood Pressure Holter Monitoring"],
    "Endocrinology": ["Serum TSH & Free T4 Panel", "Fasting Blood Glucose", "Hemoglobin A1c (HbA1c)", "Complete Blood Count (CBC)"],
    "Pulmonology": ["Chest X-Ray (PA View)", "Peak Expiratory Flow Rate (PEFR)", "Complete Blood Count (CBC)", "Oxygen Saturation Tracking"],
    "Gastroenterology": ["Complete Blood Count (CBC)", "Liver Function Tests (LFT)", "Upper GI Endoscopy (if refractory)", "H. Pylori Stool Antigen"],
    "General Medicine": ["Complete Blood Count (CBC)", "Erythrocyte Sedimentation Rate (ESR)", "Urinalysis Routine", "Basic Metabolic Panel"]
}

def generate_soap_draft_report(
    db: Session,
    conversation_id: int,
    doctor_id: Optional[int] = None
) -> Dict[str, Any]:
    """
    Synthesizes chat transcript and patient context memory into a structured SOAP draft note.
    """
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        raise ValueError("Conversation not found.")

    # Check if report already exists for this conversation
    existing_report = db.query(SOAPReport).filter(SOAPReport.conversation_id == conversation_id).first()
    if existing_report:
        return {
            "id": existing_report.id,
            "conversation_id": existing_report.conversation_id,
            "department": existing_report.department,
            "subjective": existing_report.subjective,
            "objective": existing_report.objective,
            "assessment": existing_report.assessment,
            "plan": existing_report.plan,
            "suggested_tests": json.loads(existing_report.suggested_tests) if existing_report.suggested_tests else [],
            "doctor_reviewed": existing_report.doctor_reviewed,
            "doctor_notes": existing_report.doctor_notes,
            "created_at": existing_report.created_at.isoformat()
        }

    ctx = conv.patient_context
    ctx_summary = format_patient_context_summary(ctx) if ctx else {}

    symptoms_str = ", ".join(ctx_summary.get("symptoms", [])) or "Generalized symptoms reported"
    duration_str = ctx_summary.get("duration") or "Unspecified duration"
    age_str = f"{ctx_summary.get('age')} years old" if ctx_summary.get('age') else "Age unspecified"
    sex_str = ctx_summary.get("sex") or "Sex unspecified"
    meds_str = ", ".join(ctx_summary.get("medications", [])) or "None reported"
    conditions_str = ", ".join(ctx_summary.get("known_conditions", [])) or "No prior chronic illnesses documented"

    # Subjective
    subjective = (
        f"Chief Complaint & History of Present Illness:\n"
        f"Patient ({age_str}, {sex_str}) reports experiencing {symptoms_str} lasting {duration_str}.\n"
        f"Past Medical History: {conditions_str}.\n"
        f"Current Medications: {meds_str}."
    )

    # Objective
    objective = (
        f"Clinical Observations & Ingested Data:\n"
        f"- Patient-Reported Timeline: {duration_str}\n"
        f"- Documented Symptoms: {symptoms_str}\n"
        f"- Lab Reports: {json.dumps(ctx_summary.get('lab_results', {})) if ctx_summary.get('lab_results') else 'Pending initial lab workup'}"
    )

    # Department & Assessment
    dept = "General Medicine"
    if any(s in symptoms_str.lower() for s in ["chest pain", "pressure", "palpitations"]):
        dept = "Cardiology"
    elif any(s in symptoms_str.lower() for s in ["fatigue", "tired", "thyroid", "glucose"]):
        dept = "Endocrinology"
    elif any(s in symptoms_str.lower() for s in ["cough", "breath", "wheez"]):
        dept = "Pulmonology"
    elif any(s in symptoms_str.lower() for s in ["stomach", "acid", "abdomen", "nausea"]):
        dept = "Gastroenterology"

    assessment = (
        f"Preliminary Differential Considerations (Advisory Draft):\n"
        f"1. Primary clinical pattern consistent with {dept} etiology.\n"
        f"2. Exclude secondary metabolic or post-infectious etiologies.\n"
        f"3. Confirmatory diagnosis reserved for physician in-person evaluation."
    )

    # Plan
    suggested_tests = SUGGESTED_TESTS_BY_DEPT.get(dept, SUGGESTED_TESTS_BY_DEPT["General Medicine"])
    plan = (
        f"Recommended Clinical Action Plan:\n"
        f"1. In-person clinical consultation with Department of {dept}.\n"
        f"2. Preliminary diagnostic workup: {', '.join(suggested_tests[:3])}.\n"
        f"3. Re-evaluate treatment regimen upon test results."
    )

    soap = SOAPReport(
        conversation_id=conversation_id,
        patient_id=conv.user_id,
        doctor_id=doctor_id or 1,
        department=dept,
        subjective=subjective,
        objective=objective,
        assessment=assessment,
        plan=plan,
        suggested_tests=json.dumps(suggested_tests),
        doctor_reviewed=False
    )
    db.add(soap)
    db.commit()
    db.refresh(soap)

    return {
        "id": soap.id,
        "conversation_id": soap.conversation_id,
        "department": soap.department,
        "subjective": soap.subjective,
        "objective": soap.objective,
        "assessment": soap.assessment,
        "plan": soap.plan,
        "suggested_tests": suggested_tests,
        "doctor_reviewed": soap.doctor_reviewed,
        "doctor_notes": soap.doctor_notes,
        "created_at": soap.created_at.isoformat()
    }

def doctor_review_and_approve_soap(
    db: Session,
    report_id: int,
    doctor_notes: Optional[str] = None
) -> Dict[str, Any]:
    """Physician reviews, amends, and approves the draft SOAP report."""
    soap = db.query(SOAPReport).filter(SOAPReport.id == report_id).first()
    if not soap:
        raise ValueError("SOAP report not found.")

    soap.doctor_reviewed = True
    if doctor_notes:
        soap.doctor_notes = doctor_notes
    db.commit()
    db.refresh(soap)

    return {
        "id": soap.id,
        "doctor_reviewed": True,
        "doctor_notes": soap.doctor_notes,
        "message": "SOAP clinical summary approved by attending physician."
    }
