"""
Medical Safety & Triage Module for Healthcare Knowledge Navigator.
Evaluates user messages for critical red-flag emergency symptoms deterministically.
"""

import re
from typing import Tuple, Optional, Dict, Any

# Emergency Red Flag Symptom Patterns (EMERGENCY -> Immediate 911 / ER)
EMERGENCY_PATTERNS = [
    r"\b(chest pain|chest tightness|crushing chest|pain radiating to arm|pain radiating to jaw)\b",
    r"\b(difficulty breathing|shortness of breath|gasping for air|cannot breathe|severe dyspnea)\b",
    r"\b(sudden weakness|face drooping|arm numbness|speech slurred|sudden numbness|stroke symptoms|paralysis)\b",
    r"\b(unconscious|passed out|fainted|loss of consciousness|unresponsive)\b",
    r"\b(coughing up blood|severe bleeding|uncontrolled bleeding|vomiting blood)\b",
    r"\b(severe allergic reaction|anaphylaxis|swollen lips and tongue|throat closing)\b",
    r"\b(suicidal|suicide|want to die|end my life)\b"
]

# Urgent Medical Evaluation Patterns (URGENT_EVALUATION -> Seek care within 24 hours)
URGENT_PATTERNS = [
    r"\b(high fever|fever over 103|fever above 39|stiff neck and fever)\b",
    r"\b(severe abdominal pain|acute stomach pain|sharp lower right pain)\b",
    r"\b(sudden vision loss|blurred vision suddenly|flashes of light in eye)\b",
    r"\b(confusion|disorientation|sudden severe headache|worst headache of life)\b",
    r"\b(black tarry stool|blood in stool|dark coffee ground vomit)\b"
]

EMERGENCY_RESPONSE = (
    "🚨 **IMPORTANT MEDICAL SAFETY ALERT** 🚨\n\n"
    "The symptoms you described (such as severe chest discomfort, breathing difficulty, or sudden neurological/bleeding signs) "
    "can be indicators of a **medical emergency** requiring urgent clinical evaluation.\n\n"
    "**Please take immediate action:**\n"
    "• Call your local emergency hotline (**911** in the US/Canada, **112** in Europe, or your local emergency service) immediately.\n"
    "• Go to the nearest Emergency Room (ER) or Urgent Care Center.\n"
    "• Do not attempt to drive yourself if you are feeling faint, short of breath, or in severe distress.\n\n"
    "*This assistant is an educational knowledge navigator and CANNOT provide emergency medical triage or diagnosis.*"
)

URGENT_RESPONSE_HEADER = (
    "⚠️ **URGENT MEDICAL NOTICE** ⚠️\n\n"
    "The symptoms you mentioned warrant prompt evaluation by a healthcare professional within 24 hours. "
    "While this may not be an immediate life-threatening emergency, please contact an urgent care clinic or your doctor soon.\n\n"
)

def evaluate_medical_triage(user_text: str, patient_context: Optional[Dict[str, Any]] = None) -> Tuple[str, Optional[str]]:
    """
    Evaluates text for medical emergency red flags.
    Returns (triage_level, response_override_text).
    Triage levels: 'EMERGENCY', 'URGENT_EVALUATION', 'ROUTINE_CONSULTATION', 'GENERAL_INFO'
    """
    text_lower = user_text.lower()

    # 1. Check Emergency Patterns
    for pattern in EMERGENCY_PATTERNS:
        if re.search(pattern, text_lower):
            return "EMERGENCY", EMERGENCY_RESPONSE

    # 2. Check Urgent Patterns
    for pattern in URGENT_PATTERNS:
        if re.search(pattern, text_lower):
            return "URGENT_EVALUATION", None  # Allows answer generation with urgent warning header added

    # 3. Routine / General check
    if any(term in text_lower for term in ["pain", "fever", "cough", "tired", "fatigue", "nausea", "headache", "rash", "dizzy"]):
        return "ROUTINE_CONSULTATION", None

    return "GENERAL_INFO", None
