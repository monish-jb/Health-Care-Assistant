"""
Medical Intake Assistant Agent for Healthcare Knowledge Navigator.
Executes a structured, dynamic step-by-step intake conversation tailored to the specific disease or symptom.
Asks ONE question at a time with clear, plain-language option chips.
"""

from typing import List, Tuple, Optional, Dict, Any
from app.models import PatientContext
from app.patient_context import format_patient_context_summary

DISEASE_TAILORED_PROFILES = {
    "fever": {
        "symptom": "fever",
        "questions": {
            "duration": "How long have you had this fever?",
            "duration_options": ["Just started today", "1–3 days", "About a week", "More than a week"],
            "onset_pattern": "Did the fever start suddenly with chills, or build up gradually?",
            "onset_options": ["Sudden with chills", "Gradual build up", "Fluctuates up and down"],
            "associated_symptoms": "Are you experiencing chills, body aches, a cough, or sore throat?",
            "associated_options": ["Body aches", "Sore throat", "Cough / Cold", "No other symptoms"]
        }
    },
    "chest pain": {
        "symptom": "chest pain",
        "questions": {
            "duration": "When did you first notice this chest pain?",
            "duration_options": ["Just now", "A few hours ago", "1–2 days ago", "Weeks (intermittent)"],
            "onset_pattern": "Did the chest pain start suddenly, and is it constant or does it come and go?",
            "onset_options": ["Sudden and constant", "Sudden, comes and goes", "Gradual pressure"],
            "associated_symptoms": "Is the pain radiating to your left arm or jaw, and are you short of breath?",
            "associated_options": ["Left arm or jaw pain", "Shortness of breath", "Sweating/Nausea", "No other symptoms"]
        }
    },
    "abdominal pain": {
        "symptom": "abdominal pain",
        "questions": {
            "duration": "How long have you been experiencing this stomach pain?",
            "duration_options": ["Just today", "1–3 days", "About a week", "Recurring for months"],
            "onset_pattern": "Is it a sharp constant pain in one area, or cramping that comes and goes?",
            "onset_options": ["Sharp constant pain", "Cramping, comes/goes", "Dull ache all over"],
            "associated_symptoms": "Are you experiencing nausea, vomiting, bloating, or changes in your stool?",
            "associated_options": ["Nausea or vomiting", "Diarrhea or loose stools", "Constipation", "No other symptoms"]
        }
    },
    "stomach pain": {
        "symptom": "stomach pain",
        "questions": {
            "duration": "How long have you been experiencing this stomach pain?",
            "duration_options": ["Just today", "1–3 days", "About a week", "Recurring for months"],
            "onset_pattern": "Is it a sharp constant pain in one area, or cramping that comes and goes?",
            "onset_options": ["Sharp constant pain", "Cramping, comes/goes", "Dull ache all over"],
            "associated_symptoms": "Are you experiencing nausea, vomiting, bloating, or changes in your stool?",
            "associated_options": ["Nausea or vomiting", "Diarrhea or loose stools", "Constipation", "No other symptoms"]
        }
    },
    "headache": {
        "symptom": "headache",
        "questions": {
            "duration": "How long have you been experiencing these headaches?",
            "duration_options": ["Started today", "Few days ago", "Over a week", "Chronic / recurring"],
            "onset_pattern": "How does the headache feel — is it a throbbing pain on one side or constant pressure?",
            "onset_options": ["Throbbing on one side", "Pressure all over", "Sharp stabbing", "Dull constant ache"],
            "associated_symptoms": "Any accompanying symptoms like nausea, vision changes, or sensitivity to light?",
            "associated_options": ["Nausea", "Vision changes / aura", "Sensitivity to light", "No other symptoms"]
        }
    },
    "cough": {
        "symptom": "cough",
        "questions": {
            "duration": "How long have you had this cough?",
            "duration_options": ["Less than a week", "1–3 weeks", "More than 3 weeks"],
            "onset_pattern": "Is it a dry tickly cough, or are you bringing up mucus or phlegm?",
            "onset_options": ["Dry tickly cough", "Clear / white phlegm", "Yellow / green phlegm", "Blood-tinged"],
            "associated_symptoms": "Are you experiencing wheezing, shortness of breath, or chest tightness?",
            "associated_options": ["Wheezing", "Shortness of breath", "Chest tightness", "No other symptoms"]
        }
    },
    "fatigue": {
        "symptom": "fatigue",
        "questions": {
            "duration": "How long have you been feeling this fatigue?",
            "duration_options": ["A few days", "1–2 weeks", "About a month", "Several months"],
            "onset_pattern": "Does the tiredness improve with rest, or do you still feel exhausted after sleeping well?",
            "onset_options": ["Improves with rest", "Tired even after sleep", "Hard to tell"],
            "associated_symptoms": "Have you noticed any other changes — like unexplained weight loss, night sweats, or dizziness?",
            "associated_options": ["Weight loss", "Night sweats", "Dizziness", "No other symptoms"]
        }
    },
    "tired": {
        "symptom": "fatigue",
        "questions": {
            "duration": "How long have you been feeling this fatigue?",
            "duration_options": ["A few days", "1–2 weeks", "About a month", "Several months"],
            "onset_pattern": "Does the tiredness improve with rest, or do you still feel exhausted after sleeping well?",
            "onset_options": ["Improves with rest", "Tired even after sleep", "Hard to tell"],
            "associated_symptoms": "Have you noticed any other changes — like unexplained weight loss, night sweats, or dizziness?",
            "associated_options": ["Weight loss", "Night sweats", "Dizziness", "No other symptoms"]
        }
    }
}

def evaluate_missing_clinical_context(intent: str, ctx: PatientContext) -> Tuple[bool, Optional[str], Optional[List[str]]]:
    """
    Evaluates missing intake context sequentially tailored to the stated symptom/disease.
    Returns (should_ask_followup, followup_question_text, option_chips_list).
    """
    ctx_dict = format_patient_context_summary(ctx)

    if ctx.intake_completed:
        return False, None, None

    # Step 1: Clarifying Question Retry
    if ctx.current_step == 1 and ctx.clarify_retry and not ctx.primary_complaint:
        return True, "No worries — could you describe what you're experiencing in your own words? For example: pain, itching, hair thinning, fatigue, etc.", None

    primary_sym = ctx.primary_complaint or "issue"

    # Find profile or use fallback
    profile = None
    for k, v in DISEASE_TAILORED_PROFILES.items():
        if k in primary_sym.lower():
            profile = v
            break

    # Step 1: Primary Complaint
    if ctx.current_step == 1:
        if primary_sym and primary_sym != "issue":
            ctx.current_step = 2
        else:
            return True, "What's the main health issue or primary symptom you're experiencing today?", ["Fever / Chills", "Fatigue / Weakness", "Headache / Dizziness", "Stomach / Abdominal Pain", "Cough / Respiratory", "Joint / Body Pain"]

    # Step 2: Duration
    if ctx.current_step == 2:
        if ctx_dict.get("duration"):
            ctx.current_step = 3
        else:
            if profile and "duration" in profile["questions"]:
                return True, profile["questions"]["duration"], profile["questions"]["duration_options"]
            return True, f"How many days or weeks has this {primary_sym} been going on?", ["Just started today", "1–3 days", "About a week", "More than a month"]

    # Step 3: Onset & Pattern
    if ctx.current_step == 3:
        if ctx_dict.get("onset_pattern"):
            ctx.current_step = 4
        else:
            if profile and "onset_pattern" in profile["questions"]:
                return True, profile["questions"]["onset_pattern"], profile["questions"]["onset_options"]
            return True, f"Did this {primary_sym} start suddenly or gradually? Is it constant or does it come and go?", ["Sudden & Constant", "Sudden & Comes and goes", "Gradual & Constant", "Gradual & Comes and goes"]

    # Step 4: Associated Symptoms
    if ctx.current_step == 4:
        if profile and "associated_symptoms" in profile["questions"]:
            return True, profile["questions"]["associated_symptoms"], profile["questions"]["associated_options"]
        return True, f"Are you experiencing any other symptoms along with this {primary_sym} — e.g. fever, fatigue, pain, nausea, cough?", ["Fever or chills", "Nausea or vomiting", "Cough or sore throat", "Dizziness or headache", "Body aches", "No other symptoms"]

    # Step 5: Severity
    if ctx.current_step == 5:
        if ctx_dict.get("severity"):
            ctx.current_step = 6
        else:
            return True, f"On a scale of 1–10, how severe would you say this {primary_sym} is?", ["Mild (1-3)", "Moderate (4-6)", "Severe (7-9)", "Unbearable (10)"]

    # Step 6: Pre-existing Conditions / History
    if ctx.current_step == 6:
        if ctx_dict.get("known_conditions") and ctx_dict.get("known_conditions") != []:
            ctx.current_step = 7
        else:
            return True, f"Do you have any pre-existing medical conditions (such as diabetes, BP, asthma, thyroid) that relate to this {primary_sym}?", ["High blood pressure", "Diabetes", "Asthma / Respiratory", "Thyroid disorder", "None of these"]

    # Step 7: Current Medications
    if ctx.current_step == 7:
        if ctx_dict.get("medications") and ctx_dict.get("medications") != []:
            ctx.current_step = 8
        else:
            return True, f"Are you currently taking any prescription medications or supplements to manage this {primary_sym}?", ["Pain relievers (Ibuprofen/Paracetamol)", "Yes, prescription meds", "Yes, other supplements", "No medications"]

    # Step 8: Allergies
    if ctx.current_step == 8:
        if ctx_dict.get("allergies"):
            ctx.current_step = 9
        else:
            return True, "Do you have any known allergies to drugs, food, or environmental triggers?", ["Penicillin / Antibiotics", "NSAIDs / Aspirin", "Food allergies", "No known allergies"]

    # Step 9: Recent Exposure / Triggers
    if ctx.current_step == 9:
        if ctx_dict.get("recent_exposure"):
            ctx.current_step = 10
        else:
            return True, f"Have you had any recent travel, contact with a sick person, new foods, or environmental triggers related to this {primary_sym}?", ["Contact with sick person", "Recent travel", "Dietary change / new food", "No recent triggers"]

    # Step 10: Safety Red Flag check
    if ctx.current_step == 10:
        return True, f"Red Flag Safety Check: Along with the {primary_sym}, are you experiencing difficulty breathing, chest pain, severe bleeding, confusion, or fainting?", ["Yes, experiencing red flags", "No, none of these"]

    # All steps completed
    ctx.intake_completed = True
    return False, None, None
