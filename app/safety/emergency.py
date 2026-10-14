RULES = [
    (["chest pain", "chest tightness"], "possible heart attack"),
    (["can't breathe", "cannot breathe", "difficulty breathing"], "severe breathing difficulty"),
]

def detect_emergency(text: str):
    text = text.lower()
    for phrases, reason in RULES:
        for phrase in phrases:
            if phrase in text:
                return {"reason": reason}
    return None