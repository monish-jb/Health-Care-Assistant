from app.safety.emergency import detect_emergency

def test_chest_pain():
    r = detect_emergency("I have chest pain")
    assert r is not None
    assert r["reason"] == "possible heart attack"

def test_normal_message():
    assert detect_emergency("I have a mild cold") is None

def test_uppercase():
    assert detect_emergency("CHEST PAIN since morning") is not None

def test_negation():
    assert detect_emergency("I do not have chest pain") is None

def test_breathing():
    assert detect_emergency("I can't breathe properly") is not None