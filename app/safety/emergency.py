RULES = [
    (["chest pain", "chest tightness"], "possible heart attack"),
    (["can't breathe", "cant breathe", "cannot breathe", "difficulty breathing"],
     "severe breathing difficulty"),
]

NEGATIONS = ["no", "not", "don't", "dont", "never", "without", "denies"]


def is_negated(text: str, phrase: str) -> bool:
    pos = text.find(phrase)
    words_before = text[:pos].split()[-3:]          # the 3 words right before the phrase
    return any(w in NEGATIONS for w in words_before)  # the return line that was missing


def detect_emergency(text: str):
    text = text.lower()
    text = text.replace("\u2019", "'")               # turns ’ into '
    for phrases, reason in RULES:
        for phrase in phrases:
            if phrase in text and not is_negated(text, phrase):
                return {"reason": reason}
    return None