"""
Patient Context & Memory Management Module.
Tracks patient demographics, symptoms, duration, medications, known conditions, and lab values.
Enforces patient data isolation between users.
"""

import json
import re
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from app.models import PatientContext

def get_or_create_patient_context(db: Session, conversation_id: int, user_id: int) -> PatientContext:
    """Retrieve existing patient context for conversation or create isolated record."""
    ctx = db.query(PatientContext).filter(
        PatientContext.conversation_id == conversation_id,
        PatientContext.user_id == user_id
    ).first()

    if not ctx:
        ctx = PatientContext(
            conversation_id=conversation_id,
            user_id=user_id,
            symptoms="[]",
            medications="[]",
            known_conditions="[]",
            lab_results="{}"
        )
        db.add(ctx)
        db.commit()
        db.refresh(ctx)

    return ctx

def extract_patient_entities(text: str) -> Dict[str, Any]:
    """Regex & heuristic entity extractor for medical context."""
    extracted = {}
    text_lower = text.lower()

    # Age extraction
    age_match = re.search(r'\b(\d{1,3})\s*(years old|year old|yo|y/o|yr old|yrs old)\b', text_lower)
    if not age_match:
        age_match = re.search(r'\b(age|aged)\s*(\d{1,3})\b', text_lower)
    if age_match:
        try:
            val = int(age_match.group(1) if age_match.group(1).isdigit() else age_match.group(2))
            if 0 <= val <= 120:
                extracted["age"] = val
        except ValueError:
            pass

    # Sex / Gender extraction
    if re.search(r'\b(female|woman|lady|mother|mom|sister|daughter|she|her)\b', text_lower):
        extracted["sex"] = "Female"
    elif re.search(r'\b(male|man|gentleman|father|dad|brother|son|he|him)\b', text_lower):
        extracted["sex"] = "Male"

    # Duration extraction: exclude age expressions like "62 years old"
    all_duration_matches = re.finditer(r'\b(\d+|a|few|several|couple of)\s*(days?|weeks?|months?|years?)\b', text_lower)
    for m in all_duration_matches:
        match_str = m.group(0)
        end_idx = m.end()
        following_text = text_lower[end_idx:end_idx+15]
        if not re.match(r'^\s*(old|of age|yo|y/o)', following_text):
            extracted["duration"] = match_str
            break

    # Symptom keywords
    common_symptoms = [
        "tired", "fatigue", "exhausted", "headache", "fever", "cough", "stomach pain", "nausea",
        "vomiting", "dizziness", "shortness of breath", "chest pain", "back pain", "joint pain",
        "rash", "diarrhea", "weight loss", "chills", "sore throat", "numbness", "swelling"
    ]
    found_symptoms = [s for s in common_symptoms if s in text_lower]
    if found_symptoms:
        extracted["symptoms"] = found_symptoms

    # Common Medications
    common_meds = [
        "ibuprofen", "paracetamol", "acetaminophen", "aspirin", "metformin", "lisinopril",
        "atorvastatin", "amlodipine", "omeprazole", "levothyroxine", "albuterol", "amoxicillin"
    ]
    found_meds = [m for m in common_meds if m in text_lower]
    if found_meds:
        extracted["medications"] = found_meds

    # Common Conditions
    common_conditions = [
        "diabetes", "hypertension", "high blood pressure", "asthma", "arthritis",
        "hypothyroidism", "hyperthyroidism", "anemia", "gerd", "kidney disease", "heart disease"
    ]
    found_conditions = [c for c in common_conditions if c in text_lower]
    if found_conditions:
        extracted["known_conditions"] = found_conditions

    # Lab Results extraction regex
    lab_matches = re.findall(r'\b(tsh|hemoglobin|hb|glucose|hba1c|creatinine|wbc|platelets|alt|ast)\s*(?:level|result|of|=|:)?\s*(\d+(?:\.\d+)?\s*(?:miu/l|g/dl|mg/dl|%|cells/mcl|/mcl|u/l)?)\b', text_lower)
    if lab_matches:
        labs = {}
        for test, val in lab_matches:
            labs[test.upper()] = val.strip()
        extracted["lab_results"] = labs

    return extracted

def update_patient_context_from_message(db: Session, ctx: PatientContext, user_text: str) -> PatientContext:
    """Updates PatientContext record with new entities found in user text."""
    entities = extract_patient_entities(user_text)

    if "age" in entities and not ctx.age:
        ctx.age = entities["age"]

    if "sex" in entities and not ctx.sex:
        ctx.sex = entities["sex"]

    if "duration" in entities:
        ctx.duration = entities["duration"]

    # Append new symptoms
    curr_symptoms = json.loads(ctx.symptoms) if ctx.symptoms else []
    for s in entities.get("symptoms", []):
        if s not in curr_symptoms:
            curr_symptoms.append(s)
    ctx.symptoms = json.dumps(curr_symptoms)

    # Append new medications
    curr_meds = json.loads(ctx.medications) if ctx.medications else []
    for m in entities.get("medications", []):
        if m not in curr_meds:
            curr_meds.append(m)
    ctx.medications = json.dumps(curr_meds)

    # Append new conditions
    curr_conds = json.loads(ctx.known_conditions) if ctx.known_conditions else []
    for c in entities.get("known_conditions", []):
        if c not in curr_conds:
            curr_conds.append(c)
    ctx.known_conditions = json.dumps(curr_conds)

    # Update lab results
    if "lab_results" in entities:
        curr_labs = json.loads(ctx.lab_results) if ctx.lab_results else {}
        curr_labs.update(entities["lab_results"])
        ctx.lab_results = json.dumps(curr_labs)

    db.commit()
    db.refresh(ctx)
    return ctx

def format_patient_context_summary(ctx: PatientContext) -> Dict[str, Any]:
    """Returns clean dict representation of patient context for API/Prompt."""
    return {
        "id": ctx.id,
        "conversation_id": ctx.conversation_id,
        "user_id": ctx.user_id,
        "age": ctx.age,
        "sex": ctx.sex,
        "symptoms": json.loads(ctx.symptoms) if ctx.symptoms else [],
        "duration": ctx.duration,
        "medications": json.loads(ctx.medications) if ctx.medications else [],
        "known_conditions": json.loads(ctx.known_conditions) if ctx.known_conditions else [],
        "lab_results": json.loads(ctx.lab_results) if ctx.lab_results else {},
        "updated_at": ctx.updated_at
    }

def format_patient_context_for_prompt(ctx: PatientContext) -> str:
    """Format structured context string for LLM input."""
    summary = format_patient_context_summary(ctx)
    parts = []
    if summary["age"]:
        parts.append(f"Age: {summary['age']}")
    if summary["sex"]:
        parts.append(f"Sex: {summary['sex']}")
    if summary["symptoms"]:
        parts.append(f"Reported Symptoms: {', '.join(summary['symptoms'])}")
    if summary["duration"]:
        parts.append(f"Symptom Duration: {summary['duration']}")
    if summary["medications"]:
        parts.append(f"Current Medications: {', '.join(summary['medications'])}")
    if summary["known_conditions"]:
        parts.append(f"Known Pre-existing Conditions: {', '.join(summary['known_conditions'])}")
    if summary["lab_results"]:
        lab_str = ", ".join([f"{k}: {v}" for k, v in summary["lab_results"].items()])
        parts.append(f"Recent Lab Results: {lab_str}")

    return "\n".join(parts) if parts else "No specific patient profile context gathered yet."
