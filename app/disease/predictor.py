from functools import lru_cache
from pathlib import Path

import numpy as np

from app.core.config import get_settings

DISCLAIMER = ("These are possible conditions to discuss with a clinician, not a diagnosis. "
              "Seek urgent care for severe or worsening symptoms.")


class ModelUnavailable(RuntimeError):
    pass


@lru_cache
def _bundle() -> dict:
    import joblib
    path = Path(get_settings().disease_model_path)
    if not path.exists():
        raise ModelUnavailable(f"Disease model not found at {path}")
    return joblib.load(path)  # expects {"model": sklearn clf, "symptoms": [str]}; only load trusted files


def predict(symptoms: list[str], top_n: int = 3) -> dict:
    b = _bundle()
    vocab = {s: i for i, s in enumerate(b["symptoms"])}
    clean = [s.strip().lower().replace(" ", "_") for s in symptoms]
    x = np.zeros((1, len(vocab)))
    for s in clean:
        if s in vocab:
            x[0, vocab[s]] = 1
    probs = b["model"].predict_proba(x)[0]
    top = probs.argsort()[::-1][:top_n]
    return {
        "possible_conditions": [{"condition": str(b["model"].classes_[i]), "confidence": round(float(probs[i]), 3)} for i in top],
        "unrecognized_symptoms": [s for s in clean if s not in vocab],
        "disclaimer": DISCLAIMER,
    }
