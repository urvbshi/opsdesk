import pytest
from app.rules import detect_intent


def test_refund_detection():
    text = "Client suffered duplicate charge and wants a refund for the airline ticket."
    intent, matched = detect_intent(text)
    assert intent == "Refund"
    assert "refund" in matched
    assert "duplicate charge" in matched


def test_date_change_detection():
    text = "Passenger needs to reschedule and postpone departure date to next weekend."
    intent, matched = detect_intent(text)
    assert intent == "Date Change"
    assert "reschedule" in matched
    assert "postpone" in matched


def test_cancellation_detection():
    text = "Urgent request to cancel the entire reservation due to sickness."
    intent, matched = detect_intent(text)
    assert intent == "Cancellation"
    assert "cancel" in matched


def test_visa_documents_detection():
    text = "Passport number mismatch found on voucher. Needs transit visa check."
    intent, matched = detect_intent(text)
    assert intent == "Visa/Documents"
    assert "transit visa" in matched
    assert "passport" in matched


def test_payment_issue_detection():
    text = "Credit line deduction failed and 3D Secure was timed out."
    intent, matched = detect_intent(text)
    assert intent == "Payment Issue"
    assert "3d secure" in matched


def test_supplier_issue_detection():
    text = "Hotel refused check-in because room not found in their PMS."
    intent, matched = detect_intent(text)
    assert intent == "Supplier Issue"
    assert "hotel refused" in matched
    assert "room not found" in matched


def test_fallback_to_other():
    text = "Hello, general inquiry regarding future catalog offerings."
    intent, matched = detect_intent(text)
    assert intent == "Other"
    assert matched == []
