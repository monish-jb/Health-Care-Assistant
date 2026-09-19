"""Pre- and post-LLM safety checks."""
import re
from dataclasses import dataclass

DISCLAIMER = (
    "\n\nThis is general information, not medical advice or a diagnosis. "
    "Please consult a qualified healthcare professional."
)

EMERGENCY_MESSAGE = (
    "Your message describes something that may be a medical or mental-health emergency. "
    "Please contact your local emergency number right away (India: 112) or go to the nearest "
    "emergency room. If you are thinking about harming yourself, reach out to a crisis line "
    "(India: Tele-MANAS 14416) or someone you trust now. You don't have to face this alone."
)

_EMERGENCY = [
    r"chest (pain|pressure|tightness)", r"can'?t breathe|difficulty breathing|short(ness)? of breath",
    r"stroke|face droop|slurred speech", r"severe bleeding|bleeding (heavily|won'?t stop)",
    r"unconscious|not responding|seizure", r"overdose|poison",
    r"suicid|kill myself|end my life|want to die|self[- ]harm",
]
_EMERGENCY_RE = re.compile("|".join(_EMERGENCY), re.I)

# Blocks definitive diagnoses and specific dosing instructions from model output.
_DOSAGE_RE = re.compile(r"\b\d+(\.\d+)?\s?(mg|mcg|ml|iu|units?)\b|\btake \d+\s?(tablets?|pills?|capsules?)\b", re.I)
_DIAGNOSIS_RE = re.compile(r"\byou (definitely |certainly )?(have|are suffering from|been diagnosed with)\b", re.I)

SAFE_FALLBACK = (
    "I can't give specific diagnoses or medication doses. A doctor or pharmacist can advise "
    "you based on your full history."
)


@dataclass
class InputCheck:
    emergency: bool
    message: str | None = None


def check_input(text: str) -> InputCheck:
    if _EMERGENCY_RE.search(text):
        return InputCheck(emergency=True, message=EMERGENCY_MESSAGE)
    return InputCheck(emergency=False)


def check_output(text: str) -> str:
    text = text.strip()
    if not text or _DOSAGE_RE.search(text) or _DIAGNOSIS_RE.search(text):
        text = SAFE_FALLBACK
    return text + DISCLAIMER
