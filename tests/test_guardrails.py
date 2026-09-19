from app.safety.guardrails import check_input, check_output


def test_emergency_detected():
    assert check_input("I have chest pain and can't breathe").emergency
    assert check_input("I want to end my life").emergency


def test_normal_message_allowed():
    assert not check_input("what causes a mild headache?").emergency


def test_dosage_blocked():
    assert "can't give specific" in check_output("Take 500 mg every 4 hours")


def test_diagnosis_blocked():
    assert "can't give specific" in check_output("You definitely have diabetes")


def test_disclaimer_added():
    assert "not medical advice" in check_output("Rest and drink fluids.")
