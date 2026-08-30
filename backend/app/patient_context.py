"""
Patient Context & Memory Management Module.
Tracks patient demographics, symptoms, duration, onset, severity, medications, conditions, allergies, triggers, and lab values.
Supports Structured Medical Intake Flow.
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
            lab_results="{}",
            raw_notes="[]",
            intake_completed=False,
            current_step=1,
            clarify_retry=False,
            booking_state=None,
            selected_doctor_id=None,
            selected_slot_time=None
        )
        db.add(ctx)
        db.commit()
        db.refresh(ctx)

    return ctx

def extract_patient_entities(text: str, current_step: int = 1) -> Dict[str, Any]:
    """Regex & heuristic entity extractor for medical context."""
    extracted = {}
    text_lower = text.lower().strip()

    # Age extraction: Support option chips and natural text
    if any(k in text_lower for k in ["child", "<18", "under 18"]):
        extracted["age"] = 12
    elif any(k in text_lower for k in ["adult", "18-64", "18–64", "18–40", "18-40", "41–65", "41-65"]):
        extracted["age"] = 35
    elif any(k in text_lower for k in ["senior", "65+", "over 65", "elderly"]):
        extracted["age"] = 70
    else:
        age_match = re.search(r'\b(\d{1,3})\s*(years old|year old|yo|y/o|yr old|yrs old|years|yrs)\b', text_lower)
        if not age_match:
            age_match = re.search(r'\b(?:i am|im|i\'m|age|aged|am)\s*(\d{1,3})\b', text_lower)
        if not age_match and re.fullmatch(r'^\s*(\d{1,3})\s*$', text_lower):
            age_match = re.search(r'(\d{1,3})', text_lower)
        if age_match:
            try:
                val = int(age_match.group(1))
                if 0 <= val <= 120:
                    extracted["age"] = val
            except ValueError:
                pass

    # Sex / Gender extraction
    if re.search(r'\b(female|woman|lady|mother|mom|sister|daughter|she|her)\b', text_lower):
        extracted["sex"] = "Female"
    elif re.search(r'\b(male|man|gentleman|father|dad|brother|son|he|him)\b', text_lower):
        extracted["sex"] = "Male"

    # Duration extraction: Support range chips (1–3 days, 1-2 weeks, more than 1 month, etc.)
    if any(k in text_lower for k in ["started today", "today", "just started"]):
        extracted["duration"] = "1 day"
    elif "yesterday" in text_lower:
        extracted["duration"] = "2 days"
    else:
        all_duration_matches = re.finditer(r'\b(?:more than\s+)?(\d+\s*[\-–—]\s*\d+|\d+|a|few|several|couple of)\s*(days?|weeks?|months?|years?)\b', text_lower)
        for m in all_duration_matches:
            match_str = m.group(0)
            end_idx = m.end()
            following_text = text_lower[end_idx:end_idx+15]
            if not re.match(r'^\s*(old|of age|yo|y/o)', following_text):
                extracted["duration"] = match_str
                break

    # Onset & Pattern
    if any(k in text_lower for k in ["sudden", "abrupt", "gradual", "constant", "comes and goes", "intermittent", "recurring"]):
        extracted["onset_pattern"] = text.strip()

    # Severity (1-10 or mild/moderate/severe)
    sev_match = re.search(r'\b(10|[1-9])\s*(?:/10|out of 10)?\b', text_lower)
    if sev_match and any(w in text_lower for w in ["scale", "severe", "severity", "pain", "rate", "out of"]):
        extracted["severity"] = f"{sev_match.group(1)}/10"
    elif any(k in text_lower for k in ["mild", "moderate", "severe", "unbearable", "excruciating"]):
        for word in ["unbearable", "excruciating", "severe", "moderate", "mild"]:
            if word in text_lower:
                extracted["severity"] = word.capitalize()
                break

    # Symptom keywords
    common_symptoms = [
        "tired", "fatigue", "exhausted", "headache", "fever", "cough", "stomach pain", "nausea",
        "vomiting", "dizziness", "shortness of breath", "chest pain", "back pain", "joint pain",
        "rash", "diarrhea", "weight loss", "chills", "sore throat", "numbness", "swelling", "body aches"
    ]
    found_symptoms = [s for s in common_symptoms if s in text_lower]
    if found_symptoms:
        extracted["symptoms"] = found_symptoms

    # Common Medications
    common_meds = [
        "ibuprofen", "paracetamol", "acetaminophen", "aspirin", "metformin", "lisinopril",
        "atorvastatin", "amlodipine", "omeprazole", "levothyroxine", "albuterol", "amoxicillin", "pain relievers"
    ]
    found_meds = [m for m in common_meds if m in text_lower]
    if current_step == 7 and any(k in text_lower for k in ["no medications", "no meds", "none", "not taking any", "no medicines"]):
        extracted["medications"] = ["None"]
    elif found_meds:
        extracted["medications"] = found_meds

    # Common Conditions
    common_conditions = [
        "diabetes", "hypertension", "high blood pressure", "asthma", "arthritis",
        "hypothyroidism", "hyperthyroidism", "anemia", "gerd", "kidney disease", "heart disease"
    ]
    found_conditions = [c for c in common_conditions if c in text_lower]
    if current_step == 6 and any(k in text_lower for k in ["no conditions", "no pre-existing", "healthy", "none", "no illnesses", "no history of illnesses"]):
        extracted["known_conditions"] = ["None"]
    elif found_conditions:
        extracted["known_conditions"] = found_conditions

    # Allergies
    if any(k in text_lower for k in ["penicillin", "antibiotics", "nsaids", "aspirin", "food allergies", "latex", "dust", "pollen"]):
        extracted["allergies"] = text.strip()
    elif current_step == 8 and any(k in text_lower for k in ["no allergies", "no known allergies", "none"]):
        extracted["allergies"] = "None"

    # Triggers / Exposure
    if any(k in text_lower for k in ["travel", "sick person", "sick contact", "new food", "dietary change", "environmental"]):
        extracted["recent_exposure"] = text.strip()
    elif current_step == 9 and any(k in text_lower for k in ["no triggers", "no recent triggers", "no exposure", "none"]):
        extracted["recent_exposure"] = "None"

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
    text_clean = user_text.strip()
    text_lower = text_clean.lower()

    # Record old values to detect if extractor successfully populated them
    old_duration = ctx.duration
    old_onset = ctx.onset_pattern
    old_severity = ctx.severity
    old_allergies = ctx.allergies
    old_exposure = ctx.recent_exposure
    old_meds_len = len(json.loads(ctx.medications) if ctx.medications else [])
    old_conds_len = len(json.loads(ctx.known_conditions) if ctx.known_conditions else [])

    entities = extract_patient_entities(user_text, current_step=ctx.current_step)

    if "age" in entities and not ctx.age:
        ctx.age = entities["age"]

    if "sex" in entities and not ctx.sex:
        ctx.sex = entities["sex"]

    if "duration" in entities:
        ctx.duration = entities["duration"]

    if "onset_pattern" in entities:
        ctx.onset_pattern = entities["onset_pattern"]

    if "severity" in entities:
        ctx.severity = entities["severity"]

    if "allergies" in entities:
        ctx.allergies = entities["allergies"]

    if "recent_exposure" in entities:
        ctx.recent_exposure = entities["recent_exposure"]

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

    # Step 1: Generalized Primary Complaint Extraction
    if ctx.current_step == 1 and not ctx.primary_complaint:
        ambiguous_terms = ["none", "no", "not sure", "idk", "nothing", "hello", "hi", "test", "not really", "unclear", "skip"]
        is_ambiguous = text_lower in ambiguous_terms or len(text_lower) < 3
        
        if is_ambiguous:
            if not ctx.clarify_retry:
                ctx.clarify_retry = True
            else:
                ctx.primary_complaint = "unspecified symptoms"
                ctx.symptoms = json.dumps(["unspecified symptoms"])
                ctx.current_step = 2
        else:
            ctx.primary_complaint = text_clean
            curr_symptoms = json.loads(ctx.symptoms) if ctx.symptoms else []
            if not curr_symptoms:
                curr_symptoms.append(text_clean)
            ctx.symptoms = json.dumps(curr_symptoms)
            ctx.current_step = 2
    
    # Non-Step 1 steps evaluation: check if field updated, else raw note
    elif ctx.current_step >= 2 and ctx.current_step <= 10:
        field_updated = False
        step = ctx.current_step
        
        if step == 2 and ctx.duration != old_duration:
            field_updated = True
        elif step == 3 and ctx.onset_pattern != old_onset:
            field_updated = True
        elif step == 5 and ctx.severity != old_severity:
            field_updated = True
        elif step == 6 and len(json.loads(ctx.known_conditions) if ctx.known_conditions else []) > old_conds_len:
            field_updated = True
        elif step == 7 and len(json.loads(ctx.medications) if ctx.medications else []) > old_meds_len:
            field_updated = True
        elif step == 8 and ctx.allergies != old_allergies:
            field_updated = True
        elif step == 9 and ctx.recent_exposure != old_exposure:
            field_updated = True
        elif step in [4, 10]:
            field_updated = True
            
        if step >= 2 and step <= 9 and not field_updated:
            field_names = {
                2: "duration",
                3: "onset_pattern",
                5: "severity",
                6: "known_conditions",
                7: "medications",
                8: "allergies",
                9: "recent_exposure"
            }
            f_name = field_names.get(step, "general")
            raw_list = json.loads(ctx.raw_notes) if ctx.raw_notes else []
            raw_list.append(f"Unextracted {f_name} detail: {user_text}")
            ctx.raw_notes = json.dumps(raw_list)

        ctx.current_step += 1

    # Skip-ahead logic: automatically skip any steps whose clinical fields are already populated.
    ctx_dict = format_patient_context_summary(ctx)
    while ctx.current_step <= 10:
        step = ctx.current_step
        if step == 2 and ctx_dict.get("duration"):
            ctx.current_step += 1
        elif step == 3 and ctx_dict.get("onset_pattern"):
            ctx.current_step += 1
        elif step == 4 and len(ctx_dict.get("symptoms", [])) > 1:
            ctx.current_step += 1
        elif step == 5 and ctx_dict.get("severity"):
            ctx.current_step += 1
        elif step == 6 and len(ctx_dict.get("known_conditions", [])) > 0:
            ctx.current_step += 1
        elif step == 7 and len(ctx_dict.get("medications", [])) > 0:
            ctx.current_step += 1
        elif step == 8 and ctx_dict.get("allergies"):
            ctx.current_step += 1
        elif step == 9 and ctx_dict.get("recent_exposure"):
            ctx.current_step += 1
        else:
            break

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
        "primary_complaint": ctx.primary_complaint,
        "symptoms": json.loads(ctx.symptoms) if ctx.symptoms else [],
        "duration": ctx.duration,
        "onset_pattern": ctx.onset_pattern,
        "severity": ctx.severity,
        "medications": json.loads(ctx.medications) if ctx.medications else [],
        "known_conditions": json.loads(ctx.known_conditions) if ctx.known_conditions else [],
        "allergies": ctx.allergies,
        "recent_exposure": ctx.recent_exposure,
        "lab_results": json.loads(ctx.lab_results) if ctx.lab_results else {},
        "raw_notes": json.loads(ctx.raw_notes) if ctx.raw_notes else [],
        "intake_completed": ctx.intake_completed,
        "current_step": ctx.current_step,
        "clarify_retry": ctx.clarify_retry or False,
        "booking_state": ctx.booking_state,
        "selected_doctor_id": ctx.selected_doctor_id,
        "selected_slot_time": ctx.selected_slot_time,
        "updated_at": ctx.updated_at
    }

def format_patient_context_for_prompt(ctx: PatientContext) -> str:
    """Format structured context string for LLM input."""
    summary = format_patient_context_summary(ctx)
    parts = []
    if summary["primary_complaint"]:
        parts.append(f"- **Primary Complaint**: {summary['primary_complaint']}")
    elif summary["symptoms"]:
        parts.append(f"- **Primary Complaint / Symptoms**: {', '.join(summary['symptoms'])}")
    if summary["duration"]:
        parts.append(f"- **Duration**: {summary['duration']}")
    if summary["onset_pattern"]:
        parts.append(f"- **Onset & Pattern**: {summary['onset_pattern']}")
    if summary["severity"]:
        parts.append(f"- **Severity**: {summary['severity']}")
    if summary["age"]:
        parts.append(f"- **Age**: {summary['age']}")
    if summary["sex"]:
        parts.append(f"- **Sex**: {summary['sex']}")
    if summary["known_conditions"]:
        parts.append(f"- **Known Conditions**: {', '.join(summary['known_conditions'])}")
    if summary["medications"]:
        parts.append(f"- **Current Medications**: {', '.join(summary['medications'])}")
    if summary["allergies"]:
        parts.append(f"- **Allergies**: {summary['allergies']}")
    if summary["recent_exposure"]:
        parts.append(f"- **Recent Triggers / Exposure**: {summary['recent_exposure']}")
    if summary["lab_results"]:
        lab_str = ", ".join([f"{k}: {v}" for k, v in summary["lab_results"].items()])
        parts.append(f"- **Recent Lab Results**: {lab_str}")
    if summary["raw_notes"]:
        raw_notes_str = "; ".join(summary["raw_notes"])
        parts.append(f"- **Patient Conversational Notes (unextracted details)**: {raw_notes_str}")

    return "\n".join(parts) if parts else "No patient intake history gathered yet."
